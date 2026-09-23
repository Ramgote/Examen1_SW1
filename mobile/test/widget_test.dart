import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:uml_mobile_app/main.dart';

void main() {
  testWidgets('App renders successfully', (WidgetTester tester) async {
    await tester.pumpWidget(const UmlMobileApp());
    expect(find.byType(UmlMobileApp), findsOneWidget);
  });

  testWidgets('phone layout shows conversation and accepts text without overflow', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const UmlMobileApp());
    await tester.enterText(find.byType(TextField), 'ayuda');
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('ayuda'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
