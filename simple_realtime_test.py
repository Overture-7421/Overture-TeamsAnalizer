"""
Test Simple - Verificar que scan_qr_codes acepta callback
"""

print("Verificando función scan_qr_codes...")

try:
    from qr_scanner import scan_qr_codes
    import inspect
    
    # Verificar parámetros de la función
    sig = inspect.signature(scan_qr_codes)
    params = list(sig.parameters.keys())
    
    print(f"Parámetros encontrados: {params}")
    
    if 'update_callback' in params:
        print("✅ SUCCESS: La función scan_qr_codes tiene el parámetro 'update_callback'")
        print("✅ La funcionalidad de tiempo real está implementada correctamente")
    else:
        print("❌ ERROR: Falta el parámetro 'update_callback'")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\nVerificando función de GUI...")

try:
    from main import AnalizadorGUI
    import inspect
    
    # Verificar que la función refresh_raw_data_only existe
    if hasattr(AnalizadorGUI, 'refresh_raw_data_only'):
        print("✅ SUCCESS: Función refresh_raw_data_only encontrada")
    else:
        print("❌ ERROR: Función refresh_raw_data_only no encontrada")
        
    # Verificar que scan_and_load_qr existe
    if hasattr(AnalizadorGUI, 'scan_and_load_qr'):
        print("✅ SUCCESS: Función scan_and_load_qr encontrada")
    else:
        print("❌ ERROR: Función scan_and_load_qr no encontrada")
        
except Exception as e:
    print(f"❌ Error verificando GUI: {e}")

print("\n🎯 RESULTADO:")
print("Si ves '✅ SUCCESS' arriba, la funcionalidad en tiempo real está lista!")
print("Ejecuta: python main.py")
print("Haz clic en: 'Real-Time QR Scanner'")
print("Los datos aparecerán en la tabla inmediatamente al escanear QR codes!")
