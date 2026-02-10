import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class ApiClient {
  ApiClient({required this.baseUrl});

  final String baseUrl;

  Future<Map<String, dynamic>> verifyDocument(String filePath) async {
    final uri = Uri.parse('$baseUrl/verify');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('file', filePath));
    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode != 200) {
      throw Exception(_extractError(body, response.statusCode));
    }
    return jsonDecode(body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> verifyDocumentBytes(
    Uint8List bytes,
    String filename,
  ) async {
    final uri = Uri.parse('$baseUrl/verify');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: filename),
    );
    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode != 200) {
      throw Exception(_extractError(body, response.statusCode));
    }
    return jsonDecode(body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> configureGoogleVision({
    required String adminKey,
    required String credentialsJson,
  }) async {
    final uri = Uri.parse('$baseUrl/admin/google-credentials');
    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': adminKey,
      },
      body: jsonEncode({'json': credentialsJson}),
    );
    final body = response.body.isEmpty ? '{}' : response.body;
    if (response.statusCode != 200) {
      throw Exception(_extractError(body, response.statusCode));
    }
    return jsonDecode(body) as Map<String, dynamic>;
  }

  String _extractError(String body, int statusCode) {
    try {
      final parsed = jsonDecode(body);
      if (parsed is Map && parsed['detail'] != null) {
        return parsed['detail'].toString();
      }
      if (parsed is Map && parsed['message'] != null) {
        return parsed['message'].toString();
      }
    } catch (_) {}
    return 'Request failed: $statusCode';
  }
}
