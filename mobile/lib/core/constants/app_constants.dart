class AppConstants {
  static const String appName = 'UML Mobile Studio';
  static const String defaultBackendUrl = 'http://192.168.1.51:8083/api';
  static const String prefBackendUrlKey = 'uml_backend_url';
  
  // Timeout settings
  static const Duration apiTimeout = Duration(seconds: 15);
  
  // Supported CRUD actions
  static const String actionCreate = 'CREATE';
  static const String actionRead = 'READ';
  static const String actionUpdate = 'UPDATE';
  static const String actionDelete = 'DELETE';
  static const String actionList = 'LIST';
  static const String actionHelp = 'HELP';
}
