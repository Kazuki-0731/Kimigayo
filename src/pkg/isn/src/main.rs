use clap::{Parser, Subcommand};
use std::process;

mod commands;
mod config;
mod database;
mod error;
mod package;

use error::Result;

#[derive(Parser)]
#[command(name = "isn")]
#[command(about = "Kimigayo OS Package Manager", long_about = None)]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Install a package
    Install {
        /// Package name to install
        package: String,
        /// Install without asking for confirmation
        #[arg(short, long)]
        yes: bool,
    },
    /// Remove a package
    Remove {
        /// Package name to remove
        package: String,
        /// Remove without asking for confirmation
        #[arg(short, long)]
        yes: bool,
    },
    /// Update package database
    Update,
    /// Upgrade all packages
    Upgrade {
        /// Upgrade without asking for confirmation
        #[arg(short, long)]
        yes: bool,
    },
    /// Search for packages
    Search {
        /// Search query
        query: String,
    },
    /// Show package information
    Info {
        /// Package name
        package: String,
    },
    /// List installed packages
    List {
        /// Show only explicitly installed packages
        #[arg(short, long)]
        explicit: bool,
    },
    /// Verify package integrity
    Verify {
        /// Package name to verify
        package: String,
    },
    /// Security update
    SecurityUpdate {
        /// Update without asking for confirmation
        #[arg(short, long)]
        yes: bool,
    },
}

fn main() {
    let cli = Cli::parse();

    let result = match cli.command {
        Commands::Install { package, yes } => commands::install(&package, yes),
        Commands::Remove { package, yes } => commands::remove(&package, yes),
        Commands::Update => commands::update(),
        Commands::Upgrade { yes } => commands::upgrade(yes),
        Commands::Search { query } => commands::search(&query),
        Commands::Info { package } => commands::info(&package),
        Commands::List { explicit } => commands::list(explicit),
        Commands::Verify { package } => commands::verify(&package),
        Commands::SecurityUpdate { yes } => commands::security_update(yes),
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        process::exit(1);
    }
}
