use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeSet,
    fs,
    io::Write,
    path::{Component, Path, PathBuf},
};

#[derive(Serialize, Deserialize)]
struct Configuration {
    folders: Vec<PathBuf>,
}

#[derive(Clone)]
pub struct FolderStore {
    pub file: PathBuf,
}

impl FolderStore {
    pub fn from_environment() -> Result<Self> {
        let base = std::env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .filter(|p| p.is_absolute());
        let base = match base {
            Some(path) => path,
            None => home()?.join(".config"),
        };
        Ok(Self {
            file: base.join("pushtrack/config.json"),
        })
    }

    pub fn load(&self) -> Result<Vec<PathBuf>> {
        let bytes = match fs::read(&self.file) {
            Ok(bytes) => bytes,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(vec![]),
            Err(error) => return Err(error).context("Could not read saved folders"),
        };
        let config: Configuration = serde_json::from_slice(&bytes)
            .with_context(|| format!("Invalid configuration: {}", self.file.display()))?;
        let folders: Result<BTreeSet<_>> = config.folders.iter().map(|p| normalize(p)).collect();
        Ok(folders?.into_iter().collect())
    }

    pub fn add(&self, paths: &[PathBuf]) -> Result<Vec<PathBuf>> {
        let mut folders: BTreeSet<_> = self.load()?.into_iter().collect();
        for path in paths {
            let path = normalize(path)?;
            if !path.is_dir() {
                bail!("Folder not found: {}", path.display());
            }
            folders.insert(path);
        }
        let folders: Vec<_> = folders.into_iter().collect();
        self.save(&folders)?;
        Ok(folders)
    }

    pub fn remove(&self, paths: &[PathBuf]) -> Result<Vec<PathBuf>> {
        let remove: Result<BTreeSet<_>> = paths.iter().map(|p| normalize(p)).collect();
        let remove = remove?;
        let folders: Vec<_> = self
            .load()?
            .into_iter()
            .filter(|p| !remove.contains(p))
            .collect();
        self.save(&folders)?;
        Ok(folders)
    }

    pub fn roots(&self, explicit: &[PathBuf], cwd: &Path) -> Result<Vec<PathBuf>> {
        if !explicit.is_empty() {
            return explicit.iter().map(|p| normalize(p)).collect();
        }
        let saved = self.load()?;
        if saved.is_empty() {
            Ok(vec![normalize(cwd)?])
        } else {
            Ok(saved)
        }
    }

    fn save(&self, folders: &[PathBuf]) -> Result<()> {
        let parent = self
            .file
            .parent()
            .context("Configuration has no parent folder")?;
        fs::create_dir_all(parent)?;
        let mut temp = tempfile::NamedTempFile::new_in(parent)?;
        serde_json::to_writer_pretty(
            &mut temp,
            &Configuration {
                folders: folders.to_vec(),
            },
        )?;
        writeln!(temp)?;
        temp.as_file().sync_all()?;
        temp.persist(&self.file)
            .context("Could not save folder configuration")?;
        Ok(())
    }
}

fn home() -> Result<PathBuf> {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .context("HOME is not set; set XDG_CONFIG_HOME to an absolute path")
}

pub fn normalize(path: &Path) -> Result<PathBuf> {
    let path = if path == Path::new("~") {
        home()?
    } else if let Ok(rest) = path.strip_prefix("~/") {
        home()?.join(rest)
    } else if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    };
    if let Ok(canonical) = fs::canonicalize(&path) {
        return Ok(canonical);
    }
    let mut clean = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                clean.pop();
            }
            component => clean.push(component),
        }
    }
    // Resolve the existing parent even when a saved folder has been deleted.
    // This keeps /var and /private/var (and symlinked parents) equivalent.
    let mut ancestor = clean.as_path();
    let mut missing = Vec::new();
    loop {
        if let Ok(mut resolved) = fs::canonicalize(ancestor) {
            for name in missing.iter().rev() {
                resolved.push(name);
            }
            return Ok(resolved);
        }
        match (ancestor.file_name(), ancestor.parent()) {
            (Some(name), Some(parent)) => {
                missing.push(name);
                ancestor = parent;
            }
            _ => return Ok(clean),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reads_existing_config_and_preserves_add_remove_behavior() -> Result<()> {
        let temp = tempfile::tempdir()?;
        let first = temp.path().join("First Project");
        let second = temp.path().join("second");
        fs::create_dir(&first)?;
        fs::create_dir(&second)?;
        let store = FolderStore {
            file: temp.path().join("config.json"),
        };
        fs::write(
            &store.file,
            serde_json::json!({"folders": [first]}).to_string(),
        )?;
        assert_eq!(store.load()?, [normalize(&first)?]);
        assert_eq!(
            store
                .add(&[first.clone(), second.clone(), first.clone()])?
                .len(),
            2
        );
        fs::remove_dir(&second)?;
        assert_eq!(store.remove(&[second])?, [normalize(&first)?]);
        assert_eq!(
            store.roots(std::slice::from_ref(&first), Path::new("/"))?,
            [normalize(&first)?]
        );
        Ok(())
    }
    #[test]
    fn corrupt_config_and_invalid_additions_do_not_overwrite_data() -> Result<()> {
        let temp = tempfile::tempdir()?;
        let store = FolderStore {
            file: temp.path().join("config.json"),
        };
        fs::write(&store.file, b"broken json")?;
        assert!(store.add(&[temp.path().to_path_buf()]).is_err());
        assert_eq!(fs::read(&store.file)?, b"broken json");
        assert!(
            store
                .roots(&[temp.path().to_path_buf()], Path::new("/"))
                .is_ok()
        );
        Ok(())
    }
}
