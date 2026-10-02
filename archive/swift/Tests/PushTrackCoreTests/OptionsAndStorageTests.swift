import Foundation
import Testing
@testable import PushTrackCore

struct OptionsAndStorageTests {
    @Test func scanOptionsAndLiteralPaths() throws {
        let options = try CLIOptions(arguments: ["~/Projects", "/tmp/My Work", "--fetch", "--watch", "--color", "never"])
        #expect(options.command == .scan)
        #expect(options.paths == ["~/Projects", "/tmp/My Work"])
        #expect(options.fetch)
        #expect(options.watch)
        #expect(options.refreshInterval == 60)
        #expect(options.color == .never)
        let literal = try CLIOptions(arguments: ["--", "--fetch"])
        #expect(literal.paths == ["--fetch"])
        #expect(literal.fetch == false)
        #expect(try CLIOptions(arguments: []).paths.isEmpty)
    }

    @Test(arguments: [["--wat"], ["--color"], ["--color", "purple"], ["add"], ["remove"], ["list", "/tmp"], ["add", "/tmp", "--watch"]])
    func invalidArgumentsFail(arguments: [String]) {
        #expect(throws: PushTrackError.self) { try CLIOptions(arguments: arguments) }
    }

    @Test func colorRespectsTerminalAndEnvironment() throws {
        let automatic = try CLIOptions(arguments: [])
        #expect(automatic.usesColor(isTerminal: true, environment: [:]))
        #expect(automatic.usesColor(isTerminal: false, environment: [:]) == false)
        #expect(automatic.usesColor(isTerminal: true, environment: ["NO_COLOR": ""]) == false)
        #expect(automatic.usesColor(isTerminal: true, environment: ["TERM": "dumb"]) == false)
        let forced = try CLIOptions(arguments: ["--color", "always"])
        #expect(forced.usesColor(isTerminal: false, environment: ["NO_COLOR": "1"]))
    }

    @Test func foldersPersistDeduplicateAndCanBeRemovedAfterDeletion() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let first = root.appendingPathComponent("First Project")
        let second = root.appendingPathComponent("second")
        try FileManager.default.createDirectory(at: first, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: second, withIntermediateDirectories: true)
        let config = root.appendingPathComponent("settings/config.json")
        let store = FolderStore(fileURL: config)
        #expect(try store.load().isEmpty)
        #expect(try store.scanRoots(explicitPaths: [], currentDirectory: first.path) == [FolderStore.normalize(first.path)])
        try store.add([first.path, first.path + "/", second.path])
        let reloaded = FolderStore(fileURL: config)
        #expect(try reloaded.load().count == 2)
        #expect(try reloaded.scanRoots(explicitPaths: [], currentDirectory: "/") == reloaded.load())
        #expect(try reloaded.scanRoots(explicitPaths: [first.path], currentDirectory: "/") == [FolderStore.normalize(first.path)])
        try FileManager.default.removeItem(at: second)
        try store.remove([second.path])
        #expect(try store.load() == [FolderStore.normalize(first.path)])
        #expect(throws: PushTrackError.self) { try store.add([second.path]) }
        #expect(try store.load().count == 1)
    }

    @Test func corruptConfigurationIsNotOverwritten() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let config = root.appendingPathComponent("config.json")
        let data = Data("not json".utf8)
        try data.write(to: config)
        let store = FolderStore(fileURL: config)
        #expect(throws: PushTrackError.self) { try store.add([root.path]) }
        #expect(try Data(contentsOf: config) == data)
        #expect(try store.scanRoots(explicitPaths: [root.path], currentDirectory: "/").count == 1)
    }
}
