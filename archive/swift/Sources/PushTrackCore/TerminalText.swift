import Foundation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

/// Measures terminal cells, not UTF-8 bytes. Apply styles only after clipping.
public enum TerminalText {
    public static func safe(_ text: String) -> String {
        text.unicodeScalars.map { CharacterSet.controlCharacters.contains($0) ? " " : String($0) }.joined()
    }

    public static func width(_ text: String) -> Int {
        text.unicodeScalars.reduce(0) {
            let cells = Int(wcwidth(wchar_t($1.value)))
            return $0 + (cells < 0 ? 1 : cells)
        }
    }

    public static func clipped(_ text: String, to columns: Int) -> String {
        guard columns > 0 else { return "" }
        let text = safe(text)
        guard width(text) > columns else { return text }
        var result = ""
        var used = 0
        for character in text {
            let cells = width(String(character))
            guard used + cells <= columns - 1 else { break }
            result.append(character)
            used += cells
        }
        return result + "…"
    }

    public static func fit(_ text: String, to columns: Int) -> String {
        let clipped = clipped(text, to: columns)
        return clipped + String(repeating: " ", count: max(0, columns - width(clipped)))
    }

    public static func wrap(_ text: String, to columns: Int) -> [String] {
        guard columns > 0 else { return [] }
        var lines: [String] = []
        var line = ""
        for character in safe(text) {
            if width(line + String(character)) > columns {
                lines.append(line)
                line = ""
            }
            line += clipped(String(character), to: columns)
        }
        if !line.isEmpty { lines.append(line) }
        return lines
    }
}
