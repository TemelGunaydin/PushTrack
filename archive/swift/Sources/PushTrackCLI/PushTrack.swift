import Foundation
import PushTrackCore
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

@main
struct PushTrack {
    static func main() {
        setlocale(LC_ALL, "")
        do {
            exit(try run())
        } catch {
            FileHandle.standardError.write(Data("pushtrack: \(TerminalRenderer.safe(error.localizedDescription))\n".utf8))
            exit(1)
        }
    }

    private static func run() throws -> Int32 {
        let options = try CLIOptions(arguments: Array(CommandLine.arguments.dropFirst()))
        if options.help {
            print(CLIOptions.usage)
            return 0
        }
        let store = FolderStore()
        switch options.command {
        case .add:
            showFolders(try store.add(options.paths), at: store.fileURL)
            return 0
        case .remove:
            showFolders(try store.remove(options.paths), at: store.fileURL)
            return 0
        case .list:
            showFolders(try store.load(), at: store.fileURL)
            return 0
        case .scan:
            break
        }

        let environment = ProcessInfo.processInfo.environment
        let isTerminal = isatty(STDOUT_FILENO) == 1
        guard !options.watch || (isTerminal && environment["TERM"] != "dumb") else {
            throw PushTrackError("--watch interaktif bir terminal gerektirir; pipe yerine normal tarama kullanın.")
        }
        let color = options.usesColor(isTerminal: isTerminal, environment: environment)
        let interrupts = InterruptHandler()
        defer { withExtendedLifetime(interrupts) {} }
        let state = interrupts.state
        let inspector = RepositoryInspector(git: GitRunner(isCancelled: { state.receivedSignal != 0 }))
        repeat {
            let roots = try store.scanRoots(explicitPaths: options.paths, currentDirectory: FileManager.default.currentDirectoryPath)
            let discovery = RepositoryDiscovery().discover(in: roots)
            let reports = discovery.repositories.map { inspector.inspect($0, fetch: options.fetch) }
            if state.receivedSignal != 0 { return 128 + state.receivedSignal }
            let renderer = TerminalRenderer(color: color, width: terminalWidth())
            let screen = renderer.render(reports: reports, warnings: discovery.warnings, fetch: options.fetch, watch: options.watch)
            let prefix = options.watch ? "\u{1B}[H\u{1B}[2J" : ""
            FileHandle.standardOutput.write(Data((prefix + screen).utf8))
            if !options.watch {
                return reports.isEmpty || !discovery.warnings.isEmpty || reports.contains(where: { $0.state == .error }) ? 1 : 0
            }
            let nextRefresh = ProcessInfo.processInfo.systemUptime + options.refreshInterval
            while ProcessInfo.processInfo.systemUptime < nextRefresh {
                if state.receivedSignal != 0 { return 128 + state.receivedSignal }
                Thread.sleep(forTimeInterval: 0.1)
            }
        } while options.watch
        return 0
    }

    private static func showFolders(_ folders: [URL], at configuration: URL) {
        print("Kayıtlı klasörler (\(folders.count)):")
        for folder in folders { print("  \(TerminalRenderer.safe(folder.path))") }
        if folders.isEmpty { print("  Henüz klasör yok. Eklemek için: pushtrack add /proje/klasörü") }
        print("\nAyar dosyası: \(TerminalRenderer.safe(configuration.path))")
    }

    private static func terminalWidth() -> Int {
        var size = winsize()
        if ioctl(STDOUT_FILENO, TIOCGWINSZ, &size) == 0 && size.ws_col > 0 {
            return Int(size.ws_col)
        }
        return 120
    }
}
