#include <pybind11/pybind11.h>
#include <iostream>
#include "misc.hpp"

namespace py = pybind11;

int sram_patch(const std::string & rom_path, const std::string & out_path){
    Options *opt = new Options();
    if (process_rom(rom_path,out_path,*opt)) return 0;
    else return 1;
}

PYBIND11_MODULE(gba_patch, m) {
    m.def("sram_patch", &sram_patch, py::arg("rom_path"), py::arg("out_path"));
}