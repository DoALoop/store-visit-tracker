import os

# Define the base path based on what we found
base_path = "/Users/timbarnhart/AndroidStudioProjects/StoreVisitTracker/app/src/main/java/com/example/storevisittracker"

# Define the structure we want to create
structure = {
    "data/model": ["Visit.kt", "ImageUploadRequest.kt", "DuplicateCheckResponse.kt", "SaveResponse.kt"],
    "data/repository": ["VisitRepository.kt"],
    "data/api": ["ApiService.kt"],
    "ui/camera": ["CameraScreen.kt"],
    "ui/results": ["ResultsScreen.kt"],
    "ui/history": ["HistoryScreen.kt"],
    "viewmodel": ["VisitViewModel.kt"],
}

def create_structure():
    print(f"🐶 Radar is scaffolding your Android app at: {base_path}")
    
    if not os.path.exists(base_path):
        print(f"❌ Error: Base path not found! {base_path}")
        return

    for folder, files in structure.items():
        # Create directory
        full_dir_path = os.path.join(base_path, folder)
        os.makedirs(full_dir_path, exist_ok=True)
        print(f"📂 Created: {folder}")
        
        # Create empty placeholder files
        for file_name in files:
            file_path = os.path.join(full_dir_path, file_name)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    # Add a package declaration so Kotlin doesn't complain immediately
                    package_name = folder.replace("/", ".")
                    f.write(f"package com.example.storevisittracker.{package_name}\n\n// TODO: Implement {file_name}\n")
                print(f"   📄 Created: {file_name}")
            else:
                print(f"   ⚠️  Exists: {file_name}")

    print("\n✅ Scaffolding complete! Your project structure is ready.")

if __name__ == "__main__":
    create_structure()
