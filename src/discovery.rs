use crate::config::normalize;
use std::{
    collections::{BTreeSet, HashSet},
    fs,
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};

#[derive(Default)]
pub struct Discovery {
    pub repositories: Vec<PathBuf>,
    pub warnings: Vec<String>,
}

pub fn discover(roots: &[PathBuf], cancel: &AtomicBool) -> Discovery {
    let mut result = Discovery::default();
    let mut repos = BTreeSet::new();
    let mut visited = HashSet::new();
    for root in roots {
        visit(
            root,
            0,
            cancel,
            &mut repos,
            &mut visited,
            &mut result.warnings,
        );
    }
    result.repositories = repos.into_iter().collect();
    result.warnings.sort();
    result.warnings.dedup();
    result
}

fn visit(
    path: &Path,
    depth: u8,
    cancel: &AtomicBool,
    repos: &mut BTreeSet<PathBuf>,
    visited: &mut HashSet<(PathBuf, u8)>,
    warnings: &mut Vec<String>,
) {
    if cancel.load(Ordering::Relaxed) {
        return;
    }
    let path = match normalize(path) {
        Ok(path) => path,
        Err(error) => {
            warnings.push(error.to_string());
            return;
        }
    };
    if !visited.insert((path.clone(), depth)) {
        return;
    }
    if !path.is_dir() {
        warnings.push(format!("Folder not found: {}", path.display()));
        return;
    }
    if path.join(".git").exists() {
        repos.insert(path);
        return;
    }
    if depth >= 2 {
        return;
    }
    let children = match fs::read_dir(&path) {
        Ok(children) => children,
        Err(error) => {
            warnings.push(format!("Could not read {}: {error}", path.display()));
            return;
        }
    };
    for child in children {
        if cancel.load(Ordering::Relaxed) {
            return;
        }
        let child = match child {
            Ok(child) => child,
            Err(error) => {
                warnings.push(error.to_string());
                continue;
            }
        };
        let name = child.file_name();
        let name = name.to_string_lossy();
        if name.starts_with('.')
            || [
                "node_modules",
                "vendor",
                "build",
                "dist",
                "DerivedData",
                "Pods",
                "target",
            ]
            .contains(&name.as_ref())
        {
            continue;
        }
        match child.file_type() {
            Ok(kind) if kind.is_dir() => {
                visit(&child.path(), depth + 1, cancel, repos, visited, warnings)
            }
            Err(error) => warnings.push(error.to_string()),
            _ => {}
        }
    }
}
