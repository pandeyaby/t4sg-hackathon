import 'package:sqflite/sqflite.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

class LocalStore {
  static final LocalStore _instance = LocalStore._internal();
  factory LocalStore() => _instance;
  LocalStore._internal();

  Database? _db;

  Future<Database> get db async {
    if (_db != null) return _db!;
    final dir = await getApplicationDocumentsDirectory();
    final dbPath = p.join(dir.path, 'farmers.db');
    _db = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (database, version) async {
        await database.execute('''
          CREATE TABLE pending_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            status TEXT,
            created_at TEXT
          )
        ''');
        await database.execute('''
          CREATE TABLE profiles (
            farmer_id TEXT PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            offline_enabled INTEGER
          )
        ''');
      },
    );
    return _db!;
  }

  Future<int> addPendingDoc(String filePath) async {
    final database = await db;
    return database.insert('pending_docs', {
      'file_path': filePath,
      'status': 'pending',
      'created_at': DateTime.now().toIso8601String(),
    });
  }

  Future<List<Map<String, dynamic>>> listPendingDocs() async {
    final database = await db;
    return database.query('pending_docs', where: 'status = ?', whereArgs: ['pending']);
  }

  Future<void> markDocSynced(int id) async {
    final database = await db;
    await database.update(
      'pending_docs',
      {'status': 'synced'},
      where: 'id = ?',
      whereArgs: [id],
    );
  }
}
