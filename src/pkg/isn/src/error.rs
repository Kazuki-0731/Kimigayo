use thiserror::Error;

#[derive(Error, Debug)]
pub enum IsnError {
    #[error("Package not found: {0}")]
    PackageNotFound(String),

    #[error("Package already installed: {0}")]
    PackageAlreadyInstalled(String),

    #[error("Package not installed: {0}")]
    PackageNotInstalled(String),

    #[error("Dependency error: {0}")]
    DependencyError(String),

    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("Verification error: {0}")]
    VerificationError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, IsnError>;
