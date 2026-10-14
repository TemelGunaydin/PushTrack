use super::Action;
use crate::assets::{self, Progress};
use crossterm::event::{KeyCode, KeyEvent};
use std::path::PathBuf;
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ModelPhase {
    Browse,
    Confirm,
    Busy,
    Ready,
    Error,
}
pub struct ModelManager {
    pub selected: usize,
    pub choices: Vec<(String, Option<PathBuf>)>,
    pub phase: ModelPhase,
    pub progress: Option<Progress>,
    pub error: String,
    pub selected_path: Option<PathBuf>,
}
impl ModelManager {
    pub fn new(existing: Option<PathBuf>) -> Self {
        let mut choices = vec![(
            "Qwen3.5-4B Q4_K_M · GitHub".into(),
            assets::model_path().ok(),
        )];
        let selected = usize::from(existing.is_some());
        if let Some(path) = existing {
            choices.push(("Existing file · pinned Qwen3.5".into(), Some(path)));
        }
        Self {
            selected,
            choices,
            phase: ModelPhase::Browse,
            progress: None,
            error: String::new(),
            selected_path: None,
        }
    }
    pub fn path(&self) -> Option<PathBuf> {
        self.choices[self.selected].1.clone()
    }
    pub fn key(&mut self, key: KeyEvent) -> Action {
        if key.code == KeyCode::Char('q') {
            return Action::Quit(0);
        }
        if key.code == KeyCode::Esc {
            if self.phase == ModelPhase::Confirm {
                self.phase = ModelPhase::Browse;
                return Action::None;
            }
            return Action::CloseModels;
        }
        if self.phase == ModelPhase::Busy {
            return Action::None;
        }
        match key.code {
            KeyCode::Up | KeyCode::Char('k') => {
                self.selected = self.selected.saturating_sub(1);
                self.phase = ModelPhase::Browse;
                self.error.clear();
            }
            KeyCode::Down | KeyCode::Char('j') => {
                self.selected = (self.selected + 1).min(self.choices.len() - 1);
                self.phase = ModelPhase::Browse;
                self.error.clear();
            }
            KeyCode::Enter if self.phase == ModelPhase::Ready => return Action::CloseModels,
            KeyCode::Enter if self.phase == ModelPhase::Confirm => return Action::DownloadModel,
            KeyCode::Enter => {
                if self.path().is_some_and(|path| path.is_file()) {
                    return Action::SelectModel;
                }
                if self.selected == 0 {
                    self.phase = ModelPhase::Confirm;
                } else {
                    self.phase = ModelPhase::Error;
                    self.error = "Selected local model file is missing".into();
                }
            }
            KeyCode::Char('d') if self.selected == 0 => {
                if self.phase == ModelPhase::Confirm {
                    return Action::DownloadModel;
                }
                self.phase = ModelPhase::Confirm;
            }
            _ => {}
        }
        Action::None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn ready_enter_returns_to_dashboard_without_reverification() {
        let file = tempfile::NamedTempFile::new().unwrap();
        let mut models = ModelManager::new(Some(file.path().into()));
        models.phase = ModelPhase::Ready;
        models.selected_path = Some(file.path().into());
        assert_eq!(
            models.key(KeyEvent::new(
                KeyCode::Enter,
                crossterm::event::KeyModifiers::NONE
            )),
            Action::CloseModels
        );
    }
    #[test]
    fn model_selection_download_requires_confirmation_and_cancel_is_scoped() {
        let key = |code| KeyEvent::new(code, crossterm::event::KeyModifiers::NONE);
        let mut models = ModelManager::new(Some("/absent-model-fixture".into()));
        assert_eq!(models.selected, 1);
        models.key(key(KeyCode::Up));
        assert_eq!(models.selected, 0);
        assert_eq!(models.key(key(KeyCode::Char('d'))), Action::None);
        assert!(models.phase == ModelPhase::Confirm);
        assert_eq!(models.key(key(KeyCode::Enter)), Action::DownloadModel);
        assert_eq!(models.key(key(KeyCode::Esc)), Action::None);
        assert!(models.phase == ModelPhase::Browse);
        models.phase = ModelPhase::Busy;
        assert_eq!(models.key(key(KeyCode::Enter)), Action::None);
        assert_eq!(models.key(key(KeyCode::Esc)), Action::CloseModels);
        assert_eq!(models.key(key(KeyCode::Char('q'))), Action::Quit(0));
    }
}
