use pyo3::{prelude::*, exceptions::PyIOError};
use std::path::Path;
use std::fs;

mod payload_bin;
mod batteryless_patch;

/// Patch a GBA ROM to make it batteryless
///
/// Args:
///     rom_path (str): Path to input ROM file
///     out_path (str): Path to output patched ROM file
///
/// Returns:
///     None
///
/// Raises:
///     IOError: If file operations fail
///     ValueError: If ROM is invalid or already patched
#[pyfunction]
fn patch(py: Python, rom_path: String, out_path: String, auto_mode: bool) -> PyResult<()> {
    // Validate paths
    if !Path::new(&rom_path).exists() {
        return Err(PyIOError::new_err("Input ROM file does not exist"));
    }

    if Path::new(&out_path).exists() {
        fs::remove_file(&out_path).map_err(|e| {
            PyIOError::new_err(format!("Failed to remove existing output file: {}", e))
        })?;
    }

    py.allow_threads(|| {
        batteryless_patch::patch_rom(&rom_path, &out_path, auto_mode)
            .map_err(|e| PyIOError::new_err(e.to_string()))
    })
}


/// A Python module implemented in Rust.
#[pymodule]
fn batteryless_patch_rs(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(patch, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}