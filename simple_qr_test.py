"""
Test simple del escáner QR - Verifica que puede leer datos de texto
"""
import sys
sys.path.append('.')

def test_basic_qr_processing():
    """Test básico del procesamiento de datos QR"""
    print("Probando procesamiento de datos QR...")
    
    try:
        from main import AnalizadorRobot
        
        # Crear analizador
        analyzer = AnalizadorRobot()
        print("✓ AnalizadorRobot creado correctamente")
        
        # Probar datos de texto simple
        test_data = "Scouter,Team123,Match5,Yes,No,12,8,5,2"
        print(f"\nProbando datos: {test_data}")
        
        analyzer.load_qr_data(test_data)
        print("✓ Datos QR cargados correctamente")
        
        # Verificar que se cargaron
        raw_data = analyzer.get_raw_data()
        print(f"✓ Datos disponibles: {len(raw_data)} filas")
        
        if len(raw_data) > 1:
            print(f"✓ Última fila: {raw_data[-1][:5]}...")  # Mostrar primeras 5 columnas
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_qr_scanner_import():
    """Test de importación del módulo scanner"""
    print("\nProbando importación del scanner...")
    
    try:
        from qr_scanner import scan_qr_codes, test_camera
        print("✓ Módulo qr_scanner importado")
        
        # Probar función de test de cámara
        camera_ok = test_camera()
        if camera_ok:
            print("✓ Cámara accesible")
        else:
            print("⚠ Cámara no accesible (puede ser normal si no hay cámara)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en scanner: {e}")
        return False

if __name__ == "__main__":
    print("=== Test Simple del Escáner QR ===\n")
    
    success1 = test_basic_qr_processing()
    success2 = test_qr_scanner_import()
    
    print("\n" + "="*40)
    if success1 and success2:
        print("✅ TESTS BÁSICOS EXITOSOS!")
        print("\nEl escáner QR debería funcionar correctamente.")
        print("Ejecuta 'python main.py' para usar la aplicación.")
    else:
        print("❌ Algunos tests fallaron")
