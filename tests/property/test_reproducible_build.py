"""
Property-based tests for reproducible build system

Tests validate that builds are deterministic and reproducible.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from pathlib import Path

from src.build.config import BuildConfig, Architecture, SecurityLevel, ImageType
from src.build.image import build_base_image
from src.build.reproducible import (
    perform_reproducible_build,
    verify_reproducible_build,
    verify_cross_environment_reproducibility,
    BuildEnvironment,
    BuildDependency,
    BuildMetadata,
    ReproducibleBuilder,
    BuildVerifier,
)


# Strategy for reproducible build configurations
@st.composite
def reproducible_build_configs(draw):
    """Strategy for generating reproducible build configurations"""
    arch = draw(st.sampled_from(Architecture))
    security = draw(st.sampled_from(SecurityLevel))
    image_type = draw(st.sampled_from(ImageType))
    debug = draw(st.booleans())

    num_modules = draw(st.integers(min_value=0, max_value=5))
    modules = [f"module_{i}" for i in range(num_modules)]

    return BuildConfig(
        architecture=arch,
        security_level=security,
        image_type=image_type,
        reproducible=True,  # Always reproducible for these tests
        debug=debug,
        kernel_modules=modules,
    )


# **Feature: kimigayo-os-core, Property 19: 再現可能ビルド一貫性**
# **検証対象: 要件 6.1**
@pytest.mark.property
@pytest.mark.slow
@given(config=reproducible_build_configs())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_reproducible_build_consistency(config, tmp_path):
    """
    任意のソースコードに対して、Build_Systemは複数回のビルドで
    ビット同一の出力を生成しなければならない
    """
    # Perform first build
    build_dir_1 = tmp_path / "build_1"
    build_dir_1.mkdir(exist_ok=True)
    artifact_1 = perform_reproducible_build(
        config=config,
        output_dir=build_dir_1,
        build_number=1
    )

    # Perform second build
    build_dir_2 = tmp_path / "build_2"
    build_dir_2.mkdir(exist_ok=True)
    artifact_2 = perform_reproducible_build(
        config=config,
        output_dir=build_dir_2,
        build_number=2
    )

    # Verify builds are identical
    assert verify_reproducible_build(artifact_1.image, artifact_2.image), (
        f"Builds are not reproducible:\n"
        f"  Build 1 checksum: {artifact_1.image.checksum}\n"
        f"  Build 2 checksum: {artifact_2.image.checksum}\n"
        f"  Config: {config}"
    )

    # Verify checksums are identical
    assert artifact_1.image.checksum == artifact_2.image.checksum, (
        "Checksums should be identical for reproducible builds"
    )

    # Verify file sizes are identical
    assert artifact_1.image.size_bytes == artifact_2.image.size_bytes, (
        "File sizes should be identical for reproducible builds"
    )


# **Feature: kimigayo-os-core, Property 20: 環境独立ビルド**
# **検証対象: 要件 6.2**
@pytest.mark.property
@pytest.mark.slow
@given(config=reproducible_build_configs())
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_environment_independent_build(config, tmp_path):
    """
    任意のソースコードに対して、Build_Systemは異なるビルド環境で
    同一のチェックサムを生成しなければならない
    """
    # Test with multiple builds in different "environments"
    num_builds = 3
    is_reproducible, checksums = verify_cross_environment_reproducibility(
        config=config,
        output_dir=tmp_path,
        num_builds=num_builds
    )

    assert is_reproducible, (
        f"Builds are not environment-independent:\n"
        f"  Checksums: {checksums}\n"
        f"  Unique checksums: {set(checksums)}\n"
        f"  Config: {config}"
    )

    # All checksums should be the same
    assert len(set(checksums)) == 1, (
        f"Expected 1 unique checksum, got {len(set(checksums))}"
    )


@pytest.mark.property
@given(
    arch=st.sampled_from(Architecture),
    image_type=st.sampled_from(ImageType),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_reproducible_metadata_consistency(arch, image_type, tmp_path, monkeypatch):
    """
    Verify that build metadata is consistent for reproducible builds
    """
    # Set SOURCE_DATE_EPOCH for reproducible timestamps
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    config = BuildConfig(
        architecture=arch,
        image_type=image_type,
        reproducible=True
    )

    # First build
    artifact_1 = perform_reproducible_build(config, tmp_path / "build1", 1)

    # Second build
    artifact_2 = perform_reproducible_build(config, tmp_path / "build2", 2)

    # Metadata should be consistent
    assert artifact_1.image.metadata.timestamp == artifact_2.image.metadata.timestamp
    assert artifact_1.image.metadata.build_hash == artifact_2.image.metadata.build_hash
    assert artifact_1.image.metadata.reproducible == artifact_2.image.metadata.reproducible


@pytest.mark.property
@given(config=reproducible_build_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_non_reproducible_flag_difference(config, tmp_path):
    """
    Verify that non-reproducible builds may have different checksums
    (this is expected behavior, not a failure)
    """
    # Create a non-reproducible version of the config
    non_repro_config = BuildConfig(
        architecture=config.architecture,
        security_level=config.security_level,
        image_type=config.image_type,
        reproducible=False,  # Disable reproducibility
        debug=config.debug,
        kernel_modules=config.kernel_modules,
    )

    # Non-reproducible builds should raise an error in perform_reproducible_build
    with pytest.raises(ValueError, match="Reproducible build must be enabled"):
        perform_reproducible_build(non_repro_config, tmp_path, 1)


@pytest.mark.property
@given(config=reproducible_build_configs())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_reproducible_build_size_consistency(config, tmp_path):
    """
    Verify that reproducible builds produce identical file sizes
    """
    # Build twice
    build1 = perform_reproducible_build(config, tmp_path / "b1", 1)
    build2 = perform_reproducible_build(config, tmp_path / "b2", 2)

    # Sizes must be exactly the same
    assert build1.image.size_bytes == build2.image.size_bytes, (
        f"Reproducible builds should have identical sizes: "
        f"{build1.image.size_bytes} != {build2.image.size_bytes}"
    )

    # Both should meet size constraints
    assert build1.image.verify_size_constraint()
    assert build2.image.verify_size_constraint()


# **Feature: kimigayo-os-core, Property 21: ビルド依存関係記録**
# **検証対象: 要件 6.3**
@pytest.mark.property
@given(
    dep_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
    dep_version=st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Nd', 'Pc'))),
    dep_source=st.sampled_from(["system", "pip", "apk", "npm", "cargo"])
)
def test_build_dependency_recording(dep_name, dep_version, dep_source):
    """
    任意のコンポーネントに対して、Build_Systemはすべてのビルド依存関係と
    バージョンを記録しなければならない
    """
    config = BuildConfig(
        architecture=Architecture.X86_64,
        image_type=ImageType.MINIMAL,
        reproducible=True
    )

    builder = ReproducibleBuilder(config)

    # Add dependency
    builder.add_dependency(dep_name, dep_version, dep_source)

    # Verify dependency was recorded
    assert len(builder.dependencies) >= 1

    # Find the added dependency
    found = any(
        dep.name == dep_name and
        dep.version == dep_version and
        dep.source == dep_source
        for dep in builder.dependencies
    )

    assert found, f"Dependency {dep_name}@{dep_version} from {dep_source} not found"


@pytest.mark.property
def test_automatic_dependency_recording():
    """
    Verify that ReproducibleBuilder automatically records system dependencies
    """
    config = BuildConfig(
        architecture=Architecture.X86_64,
        image_type=ImageType.MINIMAL,
        reproducible=True
    )

    builder = ReproducibleBuilder(config)
    builder.record_dependencies()

    # Should have at least Python recorded
    assert len(builder.dependencies) >= 1

    # Python should be recorded
    python_deps = [d for d in builder.dependencies if d.name == "python"]
    assert len(python_deps) == 1
    assert python_deps[0].source == "system"


# **Feature: kimigayo-os-core, Property 22: ビルド検証機能**
# **検証対象: 要件 6.4**
@pytest.mark.property
@given(config=reproducible_build_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_build_cryptographic_verification(config, tmp_path):
    """
    任意のビルド出力に対して、Build_Systemはビルド再現性の
    暗号化検証を提供しなければならない
    """
    # Perform two builds
    build_dir1 = tmp_path / "build1"
    build_dir1.mkdir(exist_ok=True)
    build_dir2 = tmp_path / "build2"
    build_dir2.mkdir(exist_ok=True)

    artifact1 = perform_reproducible_build(config, build_dir1, 1)
    artifact2 = perform_reproducible_build(config, build_dir2, 2)

    # BuildVerifier should verify builds are identical
    assert BuildVerifier.verify_build(artifact1, artifact2)

    # Checksums should match
    assert artifact1.image.checksum == artifact2.image.checksum


# **Feature: kimigayo-os-core, Property 23: ビルドメタデータ包含**
# **検証対象: 要件 6.5**
@pytest.mark.property
@given(arch=st.sampled_from(Architecture), image_type=st.sampled_from(ImageType))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_build_metadata_inclusion(arch, image_type, tmp_path):
    """
    任意のイメージに対して、Build_Systemは検証用の
    ビルドメタデータを含めなければならない
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir(exist_ok=True)
    (source_dir / "test.txt").write_text("test content")

    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)

    config = BuildConfig(
        architecture=arch,
        image_type=image_type,
        reproducible=True
    )

    builder = ReproducibleBuilder(config)
    artifact = builder.build(source_dir, output_dir, build_id="metadata_test")

    # Verify metadata file exists
    metadata_path = output_dir / "build-metadata.json"
    assert metadata_path.exists(), "Build metadata file must be created"

    # Verify metadata is valid
    metadata = BuildVerifier.verify_metadata(metadata_path)
    assert metadata.build_id == "metadata_test"
    assert metadata.source_hash is not None
    assert metadata.output_hash is not None
    assert len(metadata.dependencies) > 0


@pytest.mark.property
@given(
    dep1_name=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    dep1_version=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Pc'))),
    dep2_name=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    dep2_version=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Pc'))),
)
def test_metadata_serialization_roundtrip(dep1_name, dep1_version, dep2_name, dep2_version):
    """
    Verify BuildMetadata can be serialized and deserialized
    """
    env = BuildEnvironment.capture()
    deps = [
        BuildDependency(dep1_name, dep1_version, "system"),
        BuildDependency(dep2_name, dep2_version, "pip")
    ]

    metadata = BuildMetadata(
        build_id="test_roundtrip",
        timestamp="2025-01-01T00:00:00",
        source_hash="abc123",
        output_hash="def456",
        config={"arch": "x86_64", "variant": "minimal"},
        environment=env,
        dependencies=deps
    )

    # Serialize to JSON
    json_str = metadata.to_json()

    # Deserialize
    restored = BuildMetadata.from_json(json_str)

    # Verify roundtrip
    assert restored.build_id == "test_roundtrip"
    assert restored.source_hash == "abc123"
    assert restored.output_hash == "def456"
    assert len(restored.dependencies) == 2
