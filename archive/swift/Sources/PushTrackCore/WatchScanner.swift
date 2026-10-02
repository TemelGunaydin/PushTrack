import Foundation

/// GitRunner is blocking, so it lives on a dedicated worker queue, not the UI
/// thread or Swift's cooperative executor. All mutable state is lock-protected.
public final class WatchScanner: @unchecked Sendable {
    private let lock = NSLock()
    private let queue = DispatchQueue(label: "pushtrack.scan", qos: .utility)
    private let work = DispatchGroup()
    private let paths: [String]
    private let configurationURL: URL
    private let currentDirectory: String
    private let fetch: Bool
    private let interrupted: @Sendable () -> Bool
    private var cancelled = false
    private var data = WatchData()

    public init(options: CLIOptions, configurationURL: URL, currentDirectory: String, interrupted: @escaping @Sendable () -> Bool) {
        paths = options.paths
        fetch = options.fetch
        self.configurationURL = configurationURL
        self.currentDirectory = currentDirectory
        self.interrupted = interrupted
    }

    public func snapshot() -> WatchData {
        lock.lock()
        defer { lock.unlock() }
        return data
    }

    public func refresh() {
        lock.lock()
        guard !cancelled, !data.isRefreshing else { lock.unlock(); return }
        data.isRefreshing = true
        data.completed = 0
        data.revision += 1
        work.enter()
        lock.unlock()
        queue.async { [self] in
            defer { work.leave() }
            scan()
        }
    }

    public func cancelAndWait() {
        lock.lock()
        cancelled = true
        lock.unlock()
        work.wait()
    }

    private var shouldStop: Bool {
        lock.lock()
        let stopped = cancelled
        lock.unlock()
        return stopped || interrupted()
    }

    private func update(_ change: (inout WatchData) -> Void) {
        lock.lock()
        defer { lock.unlock() }
        change(&data)
        data.revision += 1
    }

    private func scan() {
        defer {
            update {
                $0.isRefreshing = false
                $0.lastRefresh = Date()
            }
        }
        guard !shouldStop else { return }
        do {
            let store = FolderStore(fileURL: configurationURL)
            let roots = try store.scanRoots(explicitPaths: paths, currentDirectory: currentDirectory)
            let found = RepositoryDiscovery().discover(in: roots)
            guard !shouldStop else { return }
            update { current in
                let previous = Dictionary(uniqueKeysWithValues: current.entries.map { ($0.directory.path, $0.report) })
                current.entries = found.repositories.map { WatchEntry(directory: $0, report: previous[$0.path] ?? nil) }
                current.warnings = found.warnings
            }
            let inspector = RepositoryInspector(git: GitRunner(isCancelled: { [self] in shouldStop }))
            for (index, directory) in found.repositories.enumerated() {
                guard !shouldStop else { return }
                let report = inspector.inspect(directory, fetch: fetch)
                guard !shouldStop else { return }
                update {
                    $0.entries[index].report = report
                    $0.completed = index + 1
                }
            }
        } catch {
            update { $0.warnings = [error.localizedDescription] }
        }
    }
}
