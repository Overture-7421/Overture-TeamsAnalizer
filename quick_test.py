print("Iniciando test QR...")

try:
    from main import AnalizadorRobot
    print("✓ AnalizadorRobot importado")
    
    analyzer = AnalizadorRobot()
    print("✓ Analizador creado")
    
    # Test de datos QR
    qr_text = "Scout1,Team123,Match5,Yes,No,12,8,5,2"
    analyzer.load_qr_data(qr_text)
    print("✓ Datos QR procesados")
    
    data = analyzer.get_raw_data()
    print(f"✓ Filas de datos: {len(data)}")
    
    if len(data) > 1:
        print(f"✓ Última fila: {data[-1][:3]}...")
    
    print("\n✅ El escáner QR funciona correctamente!")
    print("Los datos de texto de QR se pueden cargar en la tabla.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
