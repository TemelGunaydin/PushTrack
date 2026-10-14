use super::Action;
use crate::draft::{Capacity, StagedDiff, forbidden, validate_subject};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use std::path::PathBuf;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum DraftPhase {
    Generating,
    Capacity,
    Editing,
    Checking,
    Reviewed,
    Error,
}
pub struct DraftDialog {
    pub path: PathBuf,
    pub input: Option<StagedDiff>,
    pub capacity: Option<Capacity>,
    pub text: String,
    pub phase: DraftPhase,
    pub error: String,
}
impl DraftDialog {
    pub fn new(path: PathBuf) -> Self {
        Self {
            path,
            input: None,
            capacity: None,
            text: String::new(),
            phase: DraftPhase::Generating,
            error: String::new(),
        }
    }
    pub fn key(&mut self, key: KeyEvent) -> Action {
        if key.code == KeyCode::Esc {
            return Action::CloseDraft;
        }
        if self.phase == DraftPhase::Capacity
            && key.code == KeyCode::Enter
            && self
                .capacity
                .as_ref()
                .is_some_and(|capacity| capacity.suggested_context.is_some())
        {
            return Action::ExpandDraft;
        }
        if self.phase != DraftPhase::Editing {
            return Action::None;
        }
        self.error.clear();
        match key.code {
            KeyCode::Char('u') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.text.clear()
            }
            KeyCode::Char(c)
                if !key
                    .modifiers
                    .intersects(KeyModifiers::CONTROL | KeyModifiers::ALT)
                    && !forbidden(c)
                    && self.text.chars().count() < 72 =>
            {
                self.text.push(c)
            }
            KeyCode::Backspace => {
                self.text.pop();
            }
            KeyCode::Enter => match validate_subject(&self.text) {
                Ok(()) => return Action::ReviewDraft,
                Err(error) => self.error = error.to_string(),
            },
            _ => {}
        }
        Action::None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn larger_context_requires_enter_and_unavailable_context_cannot_start() {
        let mut dialog = DraftDialog::new("/repo".into());
        dialog.phase = DraftPhase::Capacity;
        dialog.capacity = Some(Capacity {
            diff_bytes: 300000,
            diff_tokens: 2000,
            prompt_tokens: 6000,
            output_tokens: 192,
            context: 4096,
            suggested_context: Some(8192),
        });
        let key = |code| KeyEvent::new(code, KeyModifiers::NONE);
        assert_eq!(dialog.key(key(KeyCode::Char('m'))), Action::None);
        assert_eq!(dialog.key(key(KeyCode::Esc)), Action::CloseDraft);
        assert_eq!(dialog.key(key(KeyCode::Enter)), Action::ExpandDraft);
        dialog.capacity.as_mut().unwrap().suggested_context = None;
        assert_eq!(dialog.key(key(KeyCode::Enter)), Action::None);
    }
    #[test]
    fn modal_typing_editing_recheck_and_cancel_are_scoped() {
        let key = |code| KeyEvent::new(code, KeyModifiers::NONE);
        let mut dialog = DraftDialog::new("/repo".into());
        assert_eq!(dialog.key(key(KeyCode::Char('q'))), Action::None);
        assert!(dialog.text.is_empty());
        assert_eq!(dialog.key(key(KeyCode::Esc)), Action::CloseDraft);
        dialog.phase = DraftPhase::Editing;
        dialog.text = "Add value".into();
        dialog.key(key(KeyCode::Char('q')));
        assert_eq!(dialog.text, "Add valueq");
        dialog.key(key(KeyCode::Backspace));
        assert_eq!(dialog.text, "Add value");
        assert_eq!(dialog.key(key(KeyCode::Enter)), Action::ReviewDraft);
        dialog.key(KeyEvent::new(KeyCode::Char('u'), KeyModifiers::CONTROL));
        assert!(dialog.text.is_empty());
        assert_eq!(dialog.key(key(KeyCode::Enter)), Action::None);
        assert!(!dialog.error.is_empty());
        dialog.text = "x".repeat(72);
        dialog.key(key(KeyCode::Char('y')));
        assert_eq!(dialog.text.chars().count(), 72);
        dialog.text = "Add value".into();
        dialog.key(key(KeyCode::Char('\u{202e}')));
        assert_eq!(dialog.text, "Add value");
        dialog.phase = DraftPhase::Checking;
        dialog.key(key(KeyCode::Backspace));
        assert_eq!(dialog.text, "Add value");
    }
}
