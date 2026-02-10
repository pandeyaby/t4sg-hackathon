import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'services/api_client.dart';
import 'services/local_store.dart';

void main() {
  runApp(const FarmersForForestsApp());
}

class FarmersForForestsApp extends StatelessWidget {
  const FarmersForForestsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Farmers for Forests',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1F7A57)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F7F4),
        cardTheme: CardThemeData(
          elevation: 0,
          color: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: Color(0xFFE2E8F0)),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFFF8FAFC),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final store = LocalStore();
  final _baseUrlController = TextEditingController();
  late ApiClient _api;
  String _baseUrl = '';
  String? _lastStatus;
  StatusLevel _statusLevel = StatusLevel.info;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    final initial = _defaultBaseUrl();
    _baseUrl = initial;
    _baseUrlController.text = initial;
    _api = ApiClient(baseUrl: initial);
    _loadBaseUrl();
  }

  String _defaultBaseUrl() {
    if (kIsWeb) {
      return 'http://localhost:8004';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8004';
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
        return 'http://127.0.0.1:8004';
      case TargetPlatform.fuchsia:
        return 'http://127.0.0.1:8004';
    }
  }

  Future<void> _loadBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('api_base_url');
    final baseUrl = saved?.trim().isNotEmpty == true ? saved!.trim() : _defaultBaseUrl();
    setState(() {
      _baseUrl = baseUrl;
      _baseUrlController.text = baseUrl;
      _api = ApiClient(baseUrl: baseUrl);
    });
  }

  Future<void> _saveBaseUrl() async {
    final value = _baseUrlController.text.trim();
    if (value.isEmpty) {
      _setStatus('Base URL cannot be empty', StatusLevel.error);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', value);
    setState(() {
      _baseUrl = value;
      _api = ApiClient(baseUrl: value);
    });
    _setStatus('Server updated to $value', StatusLevel.success);
  }

  void _resetBaseUrl() {
    final value = _defaultBaseUrl();
    setState(() {
      _baseUrl = value;
      _baseUrlController.text = value;
      _api = ApiClient(baseUrl: value);
    });
    _setStatus('Server reset to $value', StatusLevel.info);
  }

  void _setStatus(String message, StatusLevel level) {
    setState(() {
      _lastStatus = message;
      _statusLevel = level;
    });
  }

  String _formatError(Object error) {
    final text = error.toString();
    if (text.startsWith('Exception: ')) {
      return text.replaceFirst('Exception: ', '');
    }
    return text;
  }

  Future<void> _pickAndVerify() async {
    setState(() {
      _loading = true;
      _lastStatus = null;
    });
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: false,
      withData: kIsWeb,
    );
    if (result == null) {
      _setStatus('No file selected', StatusLevel.info);
      setState(() {
        _loading = false;
      });
      return;
    }
    try {
      if (kIsWeb) {
        final bytes = result.files.single.bytes;
        final name = result.files.single.name;
        if (bytes == null) {
          throw Exception('No file data available');
        }
        final response = await _api.verifyDocumentBytes(bytes, name);
        _setStatus(
          response['summary']?.toString() ?? 'Verified',
          StatusLevel.success,
        );
      } else {
        final path = result.files.single.path;
        if (path == null) {
          throw Exception('No file path available');
        }
        final response = await _api.verifyDocument(path);
        _setStatus(
          response['summary']?.toString() ?? 'Verified',
          StatusLevel.success,
        );
      }
    } catch (e) {
      _setStatus(_formatError(e), StatusLevel.error);
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _pickAndSaveOffline() async {
    if (kIsWeb) {
      _setStatus('Offline save not supported on web', StatusLevel.info);
      return;
    }
    setState(() {
      _loading = true;
      _lastStatus = null;
    });
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: false,
    );
    if (result == null || result.files.single.path == null) {
      _setStatus('No file selected', StatusLevel.info);
      setState(() {
        _loading = false;
      });
      return;
    }
    final path = result.files.single.path!;
    await store.addPendingDoc(path);
    setState(() {
      _loading = false;
    });
    _setStatus('Saved for offline sync', StatusLevel.success);
  }

  Future<void> _syncPending() async {
    if (kIsWeb) {
      _setStatus('Offline sync not supported on web', StatusLevel.info);
      return;
    }
    setState(() {
      _loading = true;
      _lastStatus = null;
    });
    try {
      final pending = await store.listPendingDocs();
      if (pending.isNotEmpty) {
        int successCount = 0;
        int failCount = 0;
        String? lastError;
        for (final doc in pending) {
          try {
            await _api.verifyDocument(doc['file_path'] as String);
            await store.markDocSynced(doc['id'] as int);
            successCount += 1;
          } catch (e) {
            failCount += 1;
            lastError = _formatError(e);
          }
        }
        if (failCount > 0 && lastError != null) {
          _setStatus(
            'Synced $successCount, failed $failCount. $lastError',
            StatusLevel.error,
          );
        } else {
          _setStatus(
            'Synced $successCount, failed $failCount',
            StatusLevel.success,
          );
        }
      } else {
        _setStatus('No pending documents', StatusLevel.info);
      }
    } catch (_) {
      _setStatus('Sync failed', StatusLevel.error);
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  void _openAdminLogin() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => AdminLoginScreen(api: _api)),
    );
  }

  @override
  void dispose() {
    _baseUrlController.dispose();
    super.dispose();
  }

  Widget _buildStatusChip() {
    if (_lastStatus == null) {
      return const SizedBox.shrink();
    }
    Color background;
    Color foreground;
    IconData icon;
    switch (_statusLevel) {
      case StatusLevel.success:
        background = const Color(0xFFE7F6EE);
        foreground = const Color(0xFF1F7A57);
        icon = Icons.check_circle;
        break;
      case StatusLevel.error:
        background = const Color(0xFFFDE8E8);
        foreground = const Color(0xFFB42318);
        icon = Icons.error;
        break;
      case StatusLevel.info:
        background = const Color(0xFFF2F4F7);
        foreground = const Color(0xFF475467);
        icon = Icons.info;
        break;
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(icon, color: foreground, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _lastStatus!,
              style: TextStyle(color: foreground, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Farmers for Forests'),
        actions: [
          IconButton(
            onPressed: _openAdminLogin,
            icon: const Icon(Icons.admin_panel_settings),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Card(
                  color: const Color(0xFF0F3D2E),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.forest, color: Colors.white),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: const [
                              Text(
                                'Document Verification',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Verify farmer documents with OCR and validation.',
                                style: TextStyle(color: Color(0xFFD1E4DB)),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  color: const Color(0xFFF8FAFC),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Server Connection',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _baseUrlController,
                          decoration: const InputDecoration(
                            labelText: 'API Base URL',
                            hintText: 'http://127.0.0.1:8004',
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton(
                                onPressed: _saveBaseUrl,
                                child: const Text('Save'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: OutlinedButton(
                                onPressed: _resetBaseUrl,
                                child: const Text('Reset'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Current server: $_baseUrl',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'Actions',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _loading ? null : _pickAndVerify,
                            icon: const Icon(Icons.insert_drive_file),
                            label: Text(
                              _loading ? 'Verifying...' : 'Pick & Verify',
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: _loading ? null : _pickAndSaveOffline,
                            icon: const Icon(Icons.save_alt),
                            label: Text(
                              _loading ? 'Saving...' : 'Save for Offline Sync',
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: _loading ? null : _syncPending,
                            icon: const Icon(Icons.sync),
                            label: Text(
                              _loading ? 'Syncing...' : 'Sync When Online',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Last Result',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        _buildStatusChip(),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

enum StatusLevel { info, success, error }

class AdminLoginScreen extends StatefulWidget {
  const AdminLoginScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<AdminLoginScreen> createState() => _AdminLoginScreenState();
}

class _AdminLoginScreenState extends State<AdminLoginScreen> {
  final _adminKeyController = TextEditingController();
  final _credentialsController = TextEditingController();
  String? _status;
  bool _submitting = false;
  bool _rememberKey = true;

  @override
  void initState() {
    super.initState();
    _loadSavedAdminKey();
  }

  Future<void> _loadSavedAdminKey() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('admin_api_key') ?? '';
    if (saved.isNotEmpty) {
      _adminKeyController.text = saved;
    }
  }

  Future<void> _persistAdminKey(String key) async {
    final prefs = await SharedPreferences.getInstance();
    if (_rememberKey && key.isNotEmpty) {
      await prefs.setString('admin_api_key', key);
    } else {
      await prefs.remove('admin_api_key');
    }
  }

  Future<void> _configureVision() async {
    setState(() {
      _submitting = true;
      _status = null;
    });
    try {
      final adminKey = _adminKeyController.text.trim();
      await widget.api.configureGoogleVision(
        adminKey: adminKey,
        credentialsJson: _credentialsController.text.trim(),
      );
      await _persistAdminKey(adminKey);
      setState(() {
        _status = 'Google Vision configured successfully';
      });
    } catch (_) {
      setState(() {
        _status = 'Configuration failed';
      });
    } finally {
      setState(() {
        _submitting = false;
      });
    }
  }

  @override
  void dispose() {
    _adminKeyController.dispose();
    _credentialsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Setup')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _adminKeyController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Admin API key',
              ),
            ),
            SwitchListTile(
              value: _rememberKey,
              onChanged: (value) {
                setState(() {
                  _rememberKey = value;
                });
                _persistAdminKey(_adminKeyController.text.trim());
              },
              title: const Text('Remember admin key'),
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _credentialsController,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Google Vision JSON',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _submitting ? null : _configureVision,
              child: Text(_submitting ? 'Configuring...' : 'Configure Google Vision'),
            ),
            if (_status != null) ...[
              const SizedBox(height: 12),
              Text(_status!, style: const TextStyle(color: Colors.black54)),
            ],
          ],
        ),
      ),
    );
  }
}
