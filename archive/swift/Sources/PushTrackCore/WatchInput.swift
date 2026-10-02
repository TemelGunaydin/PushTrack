import Foundation

public enum WatchKey: Equatable {
    case up, down, pageUp, pageDown, home, end, refresh, quit
}

/// Incremental decoding: escape sequences can arrive across separate reads.
public struct WatchInput {
    private var buffer: [UInt8] = []

    public init() {}

    public mutating func consume(_ bytes: [UInt8]) -> [WatchKey] {
        buffer += bytes
        var keys: [WatchKey] = []
        while let first = buffer.first {
            if first != 0x1B {
                buffer.removeFirst()
                switch first {
                case 113, 81: keys.append(.quit)
                case 114, 82: keys.append(.refresh)
                case 106: keys.append(.down)
                case 107: keys.append(.up)
                default: break
                }
                continue
            }
            guard buffer.count > 1 else { break }
            guard buffer[1] == 91 || buffer[1] == 79 else {
                buffer.removeFirst()
                continue
            }
            guard let end = buffer.indices.dropFirst(2).first(where: { (0x40...0x7E).contains(buffer[$0]) }) else {
                if buffer.count > 32 { buffer.removeAll() }
                break
            }
            let sequence = String(decoding: buffer[2...end], as: UTF8.self)
            switch sequence {
            case "A": keys.append(.up)
            case "B": keys.append(.down)
            case "5~": keys.append(.pageUp)
            case "6~": keys.append(.pageDown)
            case "H", "1~", "7~": keys.append(.home)
            case "F", "4~", "8~": keys.append(.end)
            default: break
            }
            buffer.removeFirst(end + 1)
        }
        return keys
    }
}
