use serde::Deserialize;
use std::collections::HashSet;

pub const ALT: u32 = 1;
pub const CTRL: u32 = 2;
pub const SHIFT: u32 = 4;
pub const WIN: u32 = 8;

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct Chord {
    pub modifiers: u32,
    pub key: u16,
}

#[derive(Debug)]
pub enum Action {
    Text(String),
    Send(Chord),
}

#[derive(Debug)]
pub struct Binding {
    pub chord: Chord,
    pub name: String,
    pub action: Action,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    hotkeys: Vec<Entry>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    trigger: String,
    text: Option<String>,
    send: Option<String>,
}

fn parse_chord(source: &str) -> Result<Chord, String> {
    let mut tokens = source
        .rsplit('+')
        .map(|token| token.trim().to_ascii_uppercase());
    let key = key_code(&tokens.next().unwrap_or_default())
        .ok_or_else(|| format!("Invalid key in {source:?}"))?;
    let mut modifiers = 0;
    for token in tokens {
        let bit = match token.as_str() {
            "ALT" => ALT,
            "CTRL" => CTRL,
            "SHIFT" => SHIFT,
            "WIN" => WIN,
            _ => return Err(format!("Unknown modifier {token:?} in {source:?}")),
        };
        if modifiers & bit != 0 {
            return Err(format!("Repeated modifier in {source:?}"));
        }
        modifiers |= bit;
    }
    Ok(Chord { modifiers, key })
}

fn key_code(name: &str) -> Option<u16> {
    if name.len() == 1 && name.as_bytes()[0].is_ascii_alphanumeric() {
        return Some(u16::from(name.as_bytes()[0]));
    }
    if let Some(number) = name
        .strip_prefix('F')
        .and_then(|value| value.parse::<u16>().ok())
    {
        return (1..=24).contains(&number).then(|| 0x70 + number - 1);
    }
    Some(match name {
        "BACKSPACE" => 0x08,
        "TAB" => 0x09,
        "ENTER" => 0x0D,
        "ESC" | "ESCAPE" => 0x1B,
        "SPACE" => 0x20,
        "PAGEUP" => 0x21,
        "PAGEDOWN" => 0x22,
        "END" => 0x23,
        "HOME" => 0x24,
        "LEFT" => 0x25,
        "UP" => 0x26,
        "RIGHT" => 0x27,
        "DOWN" => 0x28,
        "INSERT" => 0x2D,
        "DELETE" => 0x2E,
        _ => return None,
    })
}

pub fn parse(source: &str) -> Result<Vec<Binding>, String> {
    let config: Config = toml::from_str(source).map_err(|error| error.to_string())?;
    if config.hotkeys.is_empty() {
        return Err("Add at least one [[hotkeys]] entry.".into());
    }

    let mut triggers = HashSet::new();
    let mut bindings = Vec::with_capacity(config.hotkeys.len());
    for entry in config.hotkeys {
        let chord = parse_chord(&entry.trigger)?;
        if chord.modifiers == 0 || chord.key == 0x7B {
            return Err(format!(
                "Use a modifier and avoid F12 in trigger {:?}.",
                entry.trigger
            ));
        }
        if !triggers.insert(chord) {
            return Err(format!("Duplicate trigger {:?}.", entry.trigger));
        }
        let action = match (entry.text, entry.send) {
            (Some(text), None) if !text.is_empty() => Action::Text(text),
            (None, Some(keys)) => Action::Send(parse_chord(&keys)?),
            _ => {
                return Err(format!(
                    "Set exactly one non-empty text or send for {:?}.",
                    entry.trigger
                ))
            }
        };
        bindings.push(Binding {
            chord,
            name: entry.trigger,
            action,
        });
    }
    for binding in &bindings {
        if let Action::Send(output) = &binding.action {
            if triggers.contains(output) {
                return Err(format!(
                    "The output of {:?} is also a registered trigger.",
                    binding.name
                ));
            }
        }
    }
    Ok(bindings)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_shipped_configuration() {
        let bindings = parse(include_str!("../hotkeys.toml")).unwrap();
        assert_eq!(bindings.len(), 3);
        assert_eq!(
            bindings[0].chord,
            Chord {
                modifiers: CTRL | ALT,
                key: b'1'.into()
            }
        );
        assert_eq!(bindings[0].name, "Ctrl+Alt+1");
        assert!(matches!(&bindings[0].action, Action::Text(text) if text == "SELECT * FROM "));
        assert!(matches!(&bindings[1].action, Action::Send(chord) if chord.key == 0x74));
    }

    #[test]
    fn accepts_unicode_text_and_rejects_conflicts() {
        let source = "[[hotkeys]]\ntrigger = 'Alt+Ctrl+K'\ntext = '한글 😀'\n";
        let bindings = parse(source).unwrap();
        assert!(matches!(&bindings[0].action, Action::Text(text) if text == "한글 😀"));
        assert_eq!(bindings[0].chord.modifiers, CTRL | ALT);
        assert!(parse(&format!(
            "{source}[[hotkeys]]\ntrigger = 'ctrl+alt+k'\ntext = 'x'"
        ))
        .is_err());
        assert!(parse(&format!(
            "{source}[[hotkeys]]\ntrigger = 'Ctrl+L'\nsend = 'Ctrl+Alt+K'"
        ))
        .is_err());
        assert!(parse("[[hotkeys]]\ntrigger = 'F5'\ntext = 'x'").is_err());
        assert!(parse("[[hotkeys]]\ntrigger = 'Ctrl+F12'\ntext = 'x'").is_err());
    }
}
