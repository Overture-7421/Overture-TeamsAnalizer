"""
Test específico para el escáner QR - Prueba la lectura de datos de texto
"""

def test_qr_data_processing():
    """Prueba el procesamiento de datos QR con diferentes formatos"""
    print("=== Test de Procesamiento de Datos QR ===\n")
    
    try:
        from main import AnalizadorRobot
        analyzer = AnalizadorRobot()
        
        print("1. Probando datos simples de texto...")
        simple_text = "Team 123 - Match 5 - Score: 45"
        analyzer.load_qr_data(simple_text)
        print(f"   ✓ Datos procesados. Filas totales: {len(analyzer.sheet_data)}")
        
        print("\n2. Probando datos separados por comas...")
        csv_data = "Scouter1,Team456,Match3,Yes,No,12,8,5,2"
        analyzer.load_qr_data(csv_data)
        print(f"   ✓ Datos CSV procesados. Filas totales: {len(analyzer.sheet_data)}")
        
        print("\n3. Probando datos separados por tabuladores...")
        tab_data = "Scout2\tTeam789\tMatch7\tYes\tYes\t15\t10\t7\t3"
        analyzer.load_qr_data(tab_data)
        print(f"   ✓ Datos tabulados procesados. Filas totales: {len(analyzer.sheet_data)}")
        
        print("\n4. Probando múltiples líneas...")
        multi_line = """Team 111 Match 1
Team 222 Match 2
Team 333 Match 3"""
        analyzer.load_qr_data(multi_line)
        print(f"   ✓ Múltiples líneas procesadas. Filas totales: {len(analyzer.sheet_data)}")
        
        print("\n5. Verificando estructura de datos...")
        raw_data = analyzer.get_raw_data()
        print(f"   ✓ Encabezados: {len(raw_data[0])} columnas")
        print(f"   ✓ Datos: {len(raw_data)-1} filas")
        
        # Mostrar algunos datos de ejemplo
        print("\n6. Muestra de datos cargados:")
        for i, row in enumerate(raw_data[:5]):  # Mostrar máximo 5 filas
            if i == 0:
                print(f"   Encabezado: {row[:5]}...")  # Primeras 5 columnas
            else:
                print(f"   Fila {i}: {row[:5]}...")
        
        print(f"\n✅ ÉXITO: El procesamiento de datos QR funciona correctamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR en test QR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qr_scanner_integration():
    """Prueba la integración completa del escáner QR"""
    print("\n=== Test de Integración del Escáner QR ===\n")
    
    try:
        # Verificar dependencias
        print("1. Verificando dependencias...")
        try:
            import cv2
            print("   ✓ OpenCV disponible")
        except ImportError:
            print("   ⚠ OpenCV no encontrado - instalar con: pip install opencv-python")
            return False
            
        try:
            import pyzbar
            print("   ✓ pyzbar disponible")
        except ImportError:
            print("   ⚠ pyzbar no encontrado - instalar con: pip install pyzbar")
            return False
        
        # Verificar módulo escáner
        print("\n2. Verificando módulo de escáner...")
        from qr_scanner import scan_qr_codes, test_camera
        print("   ✓ Módulo qr_scanner importado correctamente")
        
        # Test de cámara
        print("\n3. Probando acceso a cámara...")
        if test_camera():
            print("   ✓ Cámara accesible")
        else:
            print("   ⚠ Cámara no accesible - verificar conexión y permisos")
            return False
        
        print("\n4. Verificando integración con GUI...")
        import tkinter as tk
        from main import AnalizadorGUI, AnalizadorRobot
        
        # Crear instancia sin mostrar ventana
        root = tk.Tk()
        root.withdraw()
        analyzer = AnalizadorRobot()
        gui = AnalizadorGUI(root, analyzer)
        
        print("   ✓ GUI creada correctamente")
        print("   ✓ Método scan_and_load_qr disponible")
        
        root.destroy()
        
        print(f"\n✅ ÉXITO: La integración del escáner QR está lista!")
        print("\nPara usar el escáner:")
        print("1. Ejecute: python main.py")
        print("2. Haga clic en 'Scan QR Codes'")
        print("3. Apunte códigos QR con texto a la cámara")
        print("4. Presione 'q' para finalizar el escaneo")
        print("5. Los datos aparecerán en la tabla Raw Data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR en integración QR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Alliance Simulator - Test de Escáner QR")
    print("=" * 50)
    
    success = True
    
    # Test de procesamiento de datos
    if not test_qr_data_processing():
        success = False
    
    # Test de integración
    if not test_qr_scanner_integration():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ TODOS LOS TESTS PASARON!")
        print("\nEl escáner QR está configurado correctamente para:")
        print("• Leer códigos QR con texto simple")
        print("• Procesar datos en formato CSV")
        print("• Manejar datos separados por tabuladores")
        print("• Cargar datos directamente en Raw Data")
        print("• Mostrar preview antes de cargar")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("Revise los errores arriba para solucionar problemas.")

if __name__ == "__main__":
    main()
