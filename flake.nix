{
  description = "Build GTSAM Python wheels for macOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # All Python versions we build wheels for
        pythonVersions = {
          "310" = pkgs.python310;
          "311" = pkgs.python311;
          "312" = pkgs.python312;
          "313" = pkgs.python313;
        };

        gtsam-src = pkgs.fetchFromGitHub {
          owner = "borglab";
          repo = "gtsam";
          rev = "develop";
          sha256 = "sha256-Uf71hmnRN5sXK5gWgCGkKUQlLWQALWH332wEmMsmHZI=";
        };

        commonBuildInputs = [
          pkgs.boost
          pkgs.eigen
          pkgs.tbb
        ];

        commonCmakeFlags = [
          "-DCMAKE_BUILD_TYPE=Release"
          "-DGTSAM_USE_SYSTEM_EIGEN=ON"
          "-DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF"
          "-DGTSAM_BUILD_TESTS=OFF"
          "-DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF"
          "-DGTSAM_BUILD_UNSTABLE=OFF"
          "-DGTSAM_WITH_TBB=ON"
        ];

        # -----------------------------------------------------------
        # GTSAM C++ library (shared across all Python versions)
        # -----------------------------------------------------------
        gtsam-cpp = pkgs.stdenv.mkDerivation {
          pname = "gtsam";
          version = "4.3a1-develop";

          src = gtsam-src;

          nativeBuildInputs = [ pkgs.cmake ];
          buildInputs = commonBuildInputs;

          cmakeFlags = commonCmakeFlags ++ [
            "-DGTSAM_BUILD_PYTHON=OFF"
          ];

          meta = with pkgs.lib; {
            description = "Georgia Tech Smoothing And Mapping library";
            homepage = "https://gtsam.org/";
            license = licenses.bsd2;
          };
        };

        # -----------------------------------------------------------
        # Build a wheel for a specific Python version
        # -----------------------------------------------------------
        mkWheel = pyVer: python:
          let
            pythonPackages = python.pkgs;
            cpTag = "cp${pyVer}";
            soSuffix = "cpython-${pyVer}-darwin.so";
          in
          pkgs.stdenv.mkDerivation {
            pname = "gtsam-python-wheel-${cpTag}";
            version = "4.3a1-develop";

            src = gtsam-src;

            nativeBuildInputs = [
              pkgs.cmake
              python
              pythonPackages.setuptools
              pythonPackages.wheel
              pythonPackages.pyparsing
              pythonPackages.numpy
            ];

            buildInputs = commonBuildInputs ++ [ gtsam-cpp ];

            cmakeFlags = commonCmakeFlags ++ [
              "-DGTSAM_BUILD_PYTHON=ON"
              "-DGTSAM_PYTHON_VERSION=${python.pythonVersion}"
              "-DPython_ROOT_DIR=${python}"
              "-DPython_FIND_STRATEGY=LOCATION"
            ];

            buildPhase = ''
              make -j$NIX_BUILD_CORES
            '';

            installPhase = ''
              runHook preInstall

              cd python

              # Build the wheel
              ${python}/bin/python setup.py bdist_wheel --dist-dir ./dist

              WHEEL=$(ls dist/*.whl)
              echo "Built wheel: $WHEEL"

              # Unpack the wheel
              UNPACK_DIR=$(mktemp -d)
              ${python}/bin/python -m zipfile -e "$WHEEL" "$UNPACK_DIR"
              SO_DIR="$UNPACK_DIR/gtsam"
              DYLIB_DIR="$SO_DIR/.dylibs"
              mkdir -p "$DYLIB_DIR"

              # Find the .so file dynamically
              SO_FILE=$(ls "$SO_DIR"/gtsam.cpython-*-darwin.so 2>/dev/null | head -1)
              echo ""
              echo "=== Raw .so dependencies ==="
              otool -L "$SO_FILE"

              # Use a Python script for reliable dylib bundling
              # (avoids shell quoting issues with install_name_tool and libc++ paths)
              ${python}/bin/python ${./bundle_dylibs.py} \
                "$SO_DIR" \
                "$DYLIB_DIR" \
                "${gtsam-cpp}/lib"

              echo ""
              echo "=== Bundled dylibs ==="
              ls -la "$DYLIB_DIR"/

              echo ""
              echo "=== Fixed .so dependencies ==="
              otool -L "$SO_FILE"

              echo ""
              echo "=== Fixed libgtsam dependencies ==="
              otool -L "$DYLIB_DIR/libgtsam.4.dylib" 2>/dev/null || echo "(not bundled)"

              # Repack the wheel
              mkdir -p $out
              cd "$UNPACK_DIR"
              ${python}/bin/python -c "
import zipfile, os, sys

whl_name = os.path.basename('$WHEEL')
out_dir = '$out'
whl_path = os.path.join(out_dir, whl_name)

with zipfile.ZipFile(whl_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        for f in files:
            fpath = os.path.join(root, f)
            arcname = os.path.relpath(fpath, '.')
            zf.write(fpath, arcname)
print(f'Wrote: {whl_path}')
"

              echo ""
              echo "=== Output wheel ==="
              ls -lh $out/*.whl

              runHook postInstall
            '';

            dontFixup = true;
          };

        # Build a wheel package for each Python version
        wheelPackages = builtins.mapAttrs (ver: python:
          mkWheel ver python
        ) pythonVersions;

        # Default Python for the dev shell
        defaultPython = pythonVersions."312";
        defaultPythonPackages = defaultPython.pkgs;

      in {
        packages = {
          gtsam-cpp = gtsam-cpp;

          # Individual version targets: nix build .#gtsam-wheel-cp310
          gtsam-wheel-cp310 = wheelPackages."310";
          gtsam-wheel-cp311 = wheelPackages."311";
          gtsam-wheel-cp312 = wheelPackages."312";
          gtsam-wheel-cp313 = wheelPackages."313";

          # Default builds cp312
          gtsam-wheel = wheelPackages."312";
          default = wheelPackages."312";
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.cmake
            pkgs.boost
            pkgs.eigen
            pkgs.tbb
            defaultPython
            defaultPythonPackages.pybind11
            defaultPythonPackages.pyparsing
            defaultPythonPackages.numpy
            defaultPythonPackages.setuptools
            defaultPythonPackages.wheel
          ];

          shellHook = ''
            echo "GTSAM build shell"
            echo "  cmake, boost, eigen, tbb, python ${defaultPython.pythonVersion} available"
            echo ""
            echo "Build targets:"
            echo "  nix build              # cp312 (default)"
            echo "  nix build .#gtsam-wheel-cp310"
            echo "  nix build .#gtsam-wheel-cp311"
            echo "  nix build .#gtsam-wheel-cp312"
            echo "  nix build .#gtsam-wheel-cp313"
          '';
        };
      }
    );
}
