UDF_LIB=/opt/gpudb/udf/api/cpp/kinetica
TARGET=udf_sos_cpp_proc

CUDADIR := /usr/local/cuda
PATH := ${CUDADIR}/bin:${PATH}
LD_LIBRARY_PATH := ${CUDADIR}/lib64/:${LD_LIBRARY_PATH}

all: ${TARGET}

${TARGET}: makefile ${TARGET}.cu ${UDF_LIB}/Proc.cpp ${UDF_LIB}/Proc.hpp
	nvcc -o ${TARGET} ${TARGET}.cu ${UDF_LIB}/Proc.cpp -I${UDF_LIB} -m64
