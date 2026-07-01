#include "Proc.hpp"
#include <iostream>

// Customize as appropriate
#define CUDA_THREADS 256

inline void cudaCheck(cudaError_t err)
{
    if (err != cudaSuccess)
    {
        throw std::runtime_error(cudaGetErrorString(err));
    }
}

__global__
void sos(size_t recordCount, float* d_input, float* d_output)
{
    size_t i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < recordCount)
    {
        d_output[i] += d_input[i] * d_input[i];
    }
}

int main(int argc, char *argv[])
{
    try
    {
        kinetica::ProcData* procData = kinetica::ProcData::get();
        const kinetica::ProcData::InputDataSet& inputData = procData->getInputData();
        kinetica::ProcData::OutputDataSet& outputData = procData->getOutputData();

        // Loop through input/output table pairs

        for (size_t table = 0; table < inputData.getTableCount(); ++table)
        {
            const kinetica::ProcData::InputTable& inputTable = inputData[table];
            kinetica::ProcData::OutputTable& outputTable = outputData[table];
            kinetica::ProcData::OutputColumn& outputColumn = outputTable[1];

            size_t columnCount = inputTable.getColumnCount();
            size_t recordCount = inputTable.getSize();
            size_t cudaBlocks = recordCount / CUDA_THREADS + 1;

            // Set the output table size

            outputTable.setSize(recordCount);

            // Copy ID values from input to output table

            const kinetica::ProcData::InputColumn& inputIdColumn = inputTable[0];
            kinetica::ProcData::OutputColumn& outputIdColumn = outputTable[0];
            for (size_t row = 0; row < recordCount; ++row)
                outputIdColumn.appendValue(inputIdColumn.getValue<int16_t>(row));

            // Allocate input and output device vectors on the GPU

            float* d_input;
            cudaCheck(cudaMalloc(&d_input, recordCount * sizeof(float)));

            float* d_output;
            cudaCheck(cudaMalloc(&d_output, recordCount * sizeof(float)));

            // initialize output device vector values to 0

            cudaCheck(cudaMemset(d_output, 0, recordCount * sizeof(float)));

            // Copy input data from each input column to device vector and run
            //   the calculation; saving result to output device vector

            for (size_t column = 1; column < columnCount; ++column)
            {
                const kinetica::ProcData::InputColumn& inputColumn = inputTable[column];
                cudaCheck(cudaMemcpy(d_input, inputColumn.getData<float>(), recordCount * sizeof(float), cudaMemcpyHostToDevice));
                sos<<<cudaBlocks, CUDA_THREADS>>>(recordCount, d_input, d_output);
                cudaCheck(cudaPeekAtLastError());
            }
   
            // Copy output data from device vector to output column

            cudaCheck(cudaMemcpy(outputColumn.getData<float>(), d_output, recordCount * sizeof(float), cudaMemcpyDeviceToHost));

            // Free input and output device vectors

            cudaCheck(cudaFree(d_input));
            cudaCheck(cudaFree(d_output));
        }
        
        procData->complete();
    }   
    catch (const std::exception& ex)
    {
        std::cerr << ex.what() << std::endl;
        return 1;
    }

    return 0;
}
