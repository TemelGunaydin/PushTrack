import Foundation

public struct WatchEntry: Sendable {
    public let directory: URL
    public var report: RepositoryReport?
}

public struct WatchData: Sendable {
    public var entries: [WatchEntry] = []
    public var warnings: [String] = []
    public var isRefreshing = false
    public var completed = 0
    public var lastRefresh: Date?
    public var revision = 0

    public init() {}
}

public struct WatchLayout {
    public let width: Int
    public let height: Int
    public var isSmall: Bool { width < 49 || height < 18 }
    public var isSplit: Bool { width >= 103 }
    public var bodyHeight: Int { max(0, height - 8) }
    public var listHeight: Int { isSplit ? bodyHeight : max(6, bodyHeight - 7) }
    public var pageSize: Int { max(1, (listHeight - 2) / 2) }

    public init(columns: Int, rows: Int) {
        // Leave the last terminal column unused to avoid automatic line wrapping.
        width = max(0, columns - 1)
        height = max(1, rows)
    }
}

public struct WatchSelection {
    public private(set) var index = 0
    public private(set) var offset = 0
    private var selectedPath: String?

    public init() {}

    public mutating func reconcile(entries: [WatchEntry], pageSize: Int) {
        if let selectedPath, let found = entries.firstIndex(where: { $0.directory.path == selectedPath }) {
            index = found
        }
        clamp(entries: entries, pageSize: pageSize)
    }

    public mutating func handle(_ key: WatchKey, entries: [WatchEntry], pageSize: Int) {
        switch key {
        case .up: index -= 1
        case .down: index += 1
        case .pageUp: index -= max(1, pageSize)
        case .pageDown: index += max(1, pageSize)
        case .home: index = 0
        case .end: index = entries.count - 1
        case .refresh, .quit: break
        }
        clamp(entries: entries, pageSize: pageSize)
    }

    private mutating func clamp(entries: [WatchEntry], pageSize: Int) {
        index = min(max(0, index), max(0, entries.count - 1))
        let pageSize = max(1, pageSize)
        offset = min(max(0, offset), max(0, entries.count - pageSize))
        if index < offset { offset = index }
        if index >= offset + pageSize { offset = index - pageSize + 1 }
        selectedPath = entries.isEmpty ? nil : entries[index].directory.path
    }
}
