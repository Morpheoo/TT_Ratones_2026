try:
    print("Attempting to import simba...")
    import simba
    print(f"SimBA imported successfully! Versión: {simba.__version__}")
    
    print("Attempting to import tables...")
    import tables
    print(f"Tables versión: {tables.__version__}")
    
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
