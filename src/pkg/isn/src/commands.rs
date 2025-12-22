use crate::error::Result;
use std::process::Command;

pub fn install(package: &str, yes: bool) -> Result<()> {
    println!("Installing package: {}", package);

    // Check if running as root
    if !is_root() {
        eprintln!("Error: Package installation requires root privileges");
        eprintln!("Please run: sudo isn install {}", package);
        std::process::exit(1);
    }

    // Use apk as backend for now
    // TODO: Implement native package management in future versions
    let mut cmd = Command::new("apk");
    cmd.arg("add");

    if yes {
        cmd.arg("--no-cache");
    }

    cmd.arg(package);

    println!("Executing: apk add {} {}", if yes { "--no-cache" } else { "" }, package);

    let output = cmd.output()?;

    if output.status.success() {
        println!("✓ Package '{}' installed successfully", package);
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Failed to install package '{}':", package);
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

fn is_root() -> bool {
    unsafe { libc::geteuid() == 0 }
}

pub fn remove(package: &str, yes: bool) -> Result<()> {
    println!("Removing package: {}", package);

    if !is_root() {
        eprintln!("Error: Package removal requires root privileges");
        eprintln!("Please run: sudo isn remove {}", package);
        std::process::exit(1);
    }

    let mut cmd = Command::new("apk");
    cmd.arg("del");

    if !yes {
        // TODO: Add confirmation prompt
    }

    cmd.arg(package);

    println!("Executing: apk del {}", package);

    let output = cmd.output()?;

    if output.status.success() {
        println!("✓ Package '{}' removed successfully", package);
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Failed to remove package '{}':", package);
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn update() -> Result<()> {
    println!("Updating package database...");

    if !is_root() {
        eprintln!("Error: Package database update requires root privileges");
        eprintln!("Please run: sudo isn update");
        std::process::exit(1);
    }

    let mut cmd = Command::new("apk");
    cmd.arg("update");

    println!("Executing: apk update");

    let output = cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        print!("{}", stdout);
        println!("✓ Package database updated successfully");
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Failed to update package database:");
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn upgrade(yes: bool) -> Result<()> {
    println!("Upgrading packages...");

    if !is_root() {
        eprintln!("Error: Package upgrade requires root privileges");
        eprintln!("Please run: sudo isn upgrade");
        std::process::exit(1);
    }

    let mut cmd = Command::new("apk");
    cmd.arg("upgrade");

    if yes {
        cmd.arg("--no-cache");
    }

    println!("Executing: apk upgrade");

    let output = cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        print!("{}", stdout);
        println!("✓ Packages upgraded successfully");
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Failed to upgrade packages:");
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn search(query: &str) -> Result<()> {
    println!("Searching for: {}", query);

    let mut cmd = Command::new("apk");
    cmd.arg("search");
    cmd.arg(query);

    let output = cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if stdout.trim().is_empty() {
            println!("No packages found matching '{}'", query);
        } else {
            println!("Available packages:");
            print!("{}", stdout);
        }
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Search failed:");
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn info(package: &str) -> Result<()> {
    println!("Package information for: {}", package);

    let mut cmd = Command::new("apk");
    cmd.arg("info");
    cmd.arg(package);

    let output = cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        print!("{}", stdout);
        Ok(())
    } else {
        eprintln!("Package '{}' not found", package);
        std::process::exit(1);
    }
}

pub fn list(explicit: bool) -> Result<()> {
    println!("Listing {} packages...", if explicit { "explicitly installed" } else { "all installed" });

    let mut cmd = Command::new("apk");
    cmd.arg("list");
    cmd.arg("--installed");

    let output = cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<&str> = stdout.lines().collect();
        println!("Total packages installed: {}", lines.len());
        print!("{}", stdout);
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Failed to list packages:");
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn verify(package: &str) -> Result<()> {
    println!("Verifying package: {}", package);

    let mut cmd = Command::new("apk");
    cmd.arg("verify");
    cmd.arg(package);

    let output = cmd.output()?;

    if output.status.success() {
        println!("✓ Package '{}' verified successfully", package);
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Verification failed for package '{}':", package);
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}

pub fn security_update(yes: bool) -> Result<()> {
    println!("Running security update...");

    if !is_root() {
        eprintln!("Error: Security update requires root privileges");
        eprintln!("Please run: sudo isn security-update");
        std::process::exit(1);
    }

    // First update the package database
    println!("Step 1: Updating package database...");
    let mut update_cmd = Command::new("apk");
    update_cmd.arg("update");
    let _ = update_cmd.output()?;

    // Then upgrade all packages
    println!("Step 2: Upgrading all packages...");
    let mut upgrade_cmd = Command::new("apk");
    upgrade_cmd.arg("upgrade");

    if yes {
        upgrade_cmd.arg("--no-cache");
    }

    let output = upgrade_cmd.output()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        print!("{}", stdout);
        println!("✓ Security update completed successfully");
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        eprintln!("Security update failed:");
        eprintln!("{}", stderr);
        std::process::exit(1);
    }
}
