import sys,os,os.path
from kinetica_proc import ProcData
from skcuda import cublas
import numpy as np
import pycuda.autoinit
import pycuda.gpuarray as gpuarray

# Update PATH with location of nvcc compiler
CUDA_BIN = '/usr/local/cuda/bin'
os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.join(os.sep,os.sep.join(CUDA_BIN.split('/')))
# Set XDG_CACHE_HOME directory for PyCUDA to use for temp files;
#   will use HOME directory for temp space if not set, which for gpudb_proc
#   is /home/gpudb, where it doesn't have write access
os.environ['XDG_CACHE_HOME'] = '/tmp'

def cublas_max_element_index(h,x):
    x_gpu = gpuarray.to_gpu(x)
    return cublas.cublasIsamax(h, x.size, x_gpu.gpudata,1)

def cublas_swap_vectors(h,x,y):
    x_gpu = gpuarray.to_gpu(x)
    y_gpu = gpuarray.to_gpu(y)
    cublas.cublasSswap(h, x.size, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    return x_gpu.get(), y_gpu.get()

def cublas_add_vectors(h,x,y):
    x_gpu = gpuarray.to_gpu(x)
    y_gpu = gpuarray.to_gpu(y)
    cublas.cublasSaxpy(h, x.size, 1.0, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    return y_gpu.get()

def cublas_matrix_vector_product(h,M,x):
    M_gpu = gpuarray.to_gpu(M)
    x_gpu = gpuarray.to_gpu(x)
    y1_gpu = gpuarray.empty((M.shape[1], 1), np.float32)
    cublas.cublasSgemv(h, 'n', M.shape[1], M.shape[0], np.float32(1.0), M_gpu.gpudata, M.shape[1], x_gpu.gpudata, 1, np.float32(0.0), y1_gpu.gpudata, 1)
    return y1_gpu.get()

def cublas_vector_transpose_product(h,x):
    x_gpu = gpuarray.to_gpu(x)
    A_gpu = gpuarray.zeros((x.shape[0], x.shape[0]), np.float32)
    cublas.cublasSsyr(h, 'u', x.shape[0], 1.0, x_gpu.gpudata, 1, A_gpu.gpudata, x.shape[0])
    return A_gpu.get()

def cublas_matrix_transpose_product(h,A):
    A_gpu = gpuarray.to_gpu(A)
    C_gpu = gpuarray.zeros((A.shape[0], A.shape[0]), np.float32)
    cublas.cublasSsyrk(h, 'u', 't', A.shape[0], A.shape[1], 1.0, A_gpu.gpudata, A.shape[1], 0.0, C_gpu.gpudata, A.shape[0])
    return C_gpu.get()


def example(pd):

    np.set_printoptions(linewidth=200)

    in_table = pd.input_data[0]

    x = np.ndarray(shape=(in_table.size, 1), dtype=float).astype(np.float32)
    y = np.ndarray(shape=(in_table.size, 1), dtype=float).astype(np.float32)
    M = np.ndarray(shape=(in_table.size, 3), dtype=float).astype(np.float32)

    # Initialize vectors & matrix with database values
    for i in xrange(0, in_table.size):
        x[i,0] = in_table['x'][i]
        y[i,0] = in_table['y'][i]
        M[i,0] = in_table['x'][i]
        M[i,1] = in_table['y'][i]
        M[i,2] = in_table['z'][i]


    h = cublas.cublasCreate()
    print "x = \n%s" % x
    print "y = \n%s" % y
    print "M = \n%s" % M
    print

    print "Swap vectors x & y (cuBLAS)"
    x_swap, y_swap = cublas_swap_vectors(h,x,y)
    print "x = \n%s" % x_swap
    print "y = \n%s" % y_swap
    print

    print "Swap vectors x & y (NumPy)"
    x_swap, y_swap = x.copy(), y.copy()
    x_swap[:, 0], y_swap[:, 0] = y_swap[:, 0], x_swap[:, 0].copy()
    print "x = \n%s" % x_swap
    print "y = \n%s" % y_swap
    print

    print "Max element index (cuBLAS)"
    print cublas_max_element_index(h,x)
    print

    print "Max element index (NumPy)"
    print np.argmax(x)
    print

    print "x + y (cuBLAS)"
    print cublas_add_vectors(h,x,y)
    print

    print "x + y (NumPy)"
    print x + y
    print

    print "M T * x (cuBLAS)"
    print cublas_matrix_vector_product(h,M,x)
    print

    print "M T * x (NumPy)"
    print M.T.dot(x)
    print

    print "x * x T (cuBLAS)"
    print cublas_vector_transpose_product(h,x)
    print

    print "x * x T (NumPy)"
    print x * x.T
    print

    print "M * M T (cuBLAS)"
    print cublas_matrix_transpose_product(h,M)
    print

    print "M * M T (NumPy)"
    print M.dot(M.T)

    cublas.cublasDestroy(h)


if __name__ == "__main__":

    proc_data = ProcData()

    if int(proc_data.request_info["data_segment_number"]) + 1 == int(proc_data.request_info["data_segment_count"]):
        example(proc_data)

    proc_data.complete()
