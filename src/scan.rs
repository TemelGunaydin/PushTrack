use crate::{config::FolderStore, discovery::discover, git::Git, model::Report};
use anyhow::Result;
use std::{
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, Sender},
    },
    thread::{self, JoinHandle},
    time::{Duration, SystemTime},
};

pub enum Update {
    Started {
        paths: Vec<PathBuf>,
        warnings: Vec<String>,
    },
    Report(Report),
    Failed(String),
    Finished(SystemTime),
}

pub struct Scanner {
    pub updates: Receiver<Update>,
    sender: Sender<Update>,
    handle: Option<JoinHandle<()>>,
    pub cancel: Arc<AtomicBool>,
    store: FolderStore,
    paths: Vec<PathBuf>,
    cwd: PathBuf,
    fetch: bool,
}

impl Scanner {
    pub fn new(
        store: FolderStore,
        paths: Vec<PathBuf>,
        fetch: bool,
        cancel: Arc<AtomicBool>,
    ) -> Result<Self> {
        let (sender, updates) = mpsc::channel();
        Ok(Self {
            updates,
            sender,
            handle: None,
            cancel,
            store,
            paths,
            cwd: std::env::current_dir()?,
            fetch,
        })
    }

    pub fn start(&mut self) -> bool {
        if self.handle.as_ref().is_some_and(|h| !h.is_finished()) {
            return false;
        }
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
        if self.cancel.load(Ordering::Relaxed) {
            return false;
        }
        let (store, paths, cwd, fetch, sender, cancel) = (
            self.store.clone(),
            self.paths.clone(),
            self.cwd.clone(),
            self.fetch,
            self.sender.clone(),
            self.cancel.clone(),
        );
        self.handle = Some(thread::spawn(move || {
            let result = (|| -> Result<()> {
                let roots = store.roots(&paths, &cwd)?;
                let found = discover(&roots, &cancel);
                let _ = sender.send(Update::Started {
                    paths: found.repositories.clone(),
                    warnings: found.warnings,
                });
                let git = Git {
                    cancel: cancel.clone(),
                    timeout: Duration::from_secs(20),
                };
                for path in found.repositories {
                    if cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    let report = git.inspect(&path, fetch);
                    if cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    if sender.send(Update::Report(report)).is_err() {
                        break;
                    }
                }
                Ok(())
            })();
            if let Err(error) = result {
                let _ = sender.send(Update::Failed(format!("{error:#}")));
            }
            let _ = sender.send(Update::Finished(SystemTime::now()));
        }));
        true
    }
}

impl Drop for Scanner {
    fn drop(&mut self) {
        self.cancel.store(true, Ordering::Relaxed);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}
