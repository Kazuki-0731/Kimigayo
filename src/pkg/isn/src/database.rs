use rusqlite::{Connection, Result};

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        Ok(Self { conn })
    }

    pub fn init_schema(&self) -> Result<()> {
        self.conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL,
                description TEXT,
                installed_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS dependencies (
                package_id INTEGER,
                depends_on TEXT,
                FOREIGN KEY (package_id) REFERENCES packages(id)
            );

            CREATE INDEX IF NOT EXISTS idx_package_name ON packages(name);
            "#,
        )?;
        Ok(())
    }
}
