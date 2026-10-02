import Foundation

public struct FolderStore {
    public let fileURL: URL

    private struct Configuration: Codable {
        var folders: [String]
    }

    public init(fileURL: URL? = nil) {
        if let fileURL {
            self.fileURL = fileURL
        } else {
            let configured = ProcessInfo.processInfo.environment["XDG_CONFIG_HOME"]
            let base = configured.flatMap { $0.hasPrefix("/") ? URL(fileURLWithPath: $0) : nil }
                ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".config")
            self.fileURL = base.appendingPathComponent("pushtrack/config.json")
        }
    }

    public static func normalize(_ path: String) -> URL {
        URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
            .standardizedFileURL.resolvingSymlinksInPath()
    }

    public func load() throws -> [URL] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return [] }
        do {
            let configuration = try JSONDecoder().decode(Configuration.self, from: Data(contentsOf: fileURL))
            return Array(Set(configuration.folders.map(Self.normalize))).sorted { $0.path < $1.path }
        } catch {
            throw PushTrackError("Could not read saved folders: \(fileURL.path) — \(error.localizedDescription)")
        }
    }

    @discardableResult
    public func add(_ paths: [String]) throws -> [URL] {
        let additions = paths.map(Self.normalize)
        for url in additions {
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory),
                  isDirectory.boolValue else {
                throw PushTrackError("Folder not found: \(url.path)")
            }
        }
        let folders = Array(Set(try load()).union(additions)).sorted { $0.path < $1.path }
        try save(folders)
        return folders
    }

    @discardableResult
    public func remove(_ paths: [String]) throws -> [URL] {
        let removals = Set(paths.map(Self.normalize))
        let folders = try load().filter { !removals.contains($0) }
        try save(folders)
        return folders
    }

    public func scanRoots(explicitPaths: [String], currentDirectory: String) throws -> [URL] {
        if !explicitPaths.isEmpty { return explicitPaths.map(Self.normalize) }
        let saved = try load()
        return saved.isEmpty ? [Self.normalize(currentDirectory)] : saved
    }

    private func save(_ folders: [URL]) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(Configuration(folders: folders.map(\.path)))
        try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: fileURL, options: .atomic)
    }
}
