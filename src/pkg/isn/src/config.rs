use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct Config {
    pub database_path: PathBuf,
    pub cache_dir: PathBuf,
    pub mirrors: Vec<String>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            database_path: PathBuf::from("/var/lib/isn/db.sqlite"),
            cache_dir: PathBuf::from("/var/cache/isn"),
            mirrors: vec![
                "https://mirrors.kimigayo.org/packages".to_string(),
            ],
        }
    }
}
