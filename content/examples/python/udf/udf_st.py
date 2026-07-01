################################################################################
#                                                                              #
# Kinetica Sentence Transformer UDF Example                                    #
# ---------------------------------------------------------------------------- #
# This UDF takes a set of sentences, computes embeddings, and then ranks the   #
# sentences against a given sentence.                                          #
#                                                                              #
################################################################################

# Load the Kinetica UDF API
from kinetica_proc import ProcData

# Set the cache environment variable before loading the sentence_transformers module
#   also, use expandable segments to help with memory management issues
import os
os.environ["HF_HOME"] = "/tmp"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Load sentence_transformers library with the updated HuggingFace home directory set
from sentence_transformers import SentenceTransformer, util


# Instantiate a handle to the ProcData() class
proc_data = ProcData()

in_table = proc_data.input_data[0]
out_table = proc_data.output_data[0]

embedder = SentenceTransformer("all-MiniLM-L6-v2")
sentences = [rec for rec in in_table['sentence']]

emb = embedder.encode(sentences, convert_to_tensor = True)


# Get the sentence to match against from the request parameters,
#   then calculate the embedding for it; lastly, compute distance
#   scores between the given sentence and the reference sentences.
sentence = proc_data.params["sentence"]
sentence_emb = embedder.encode(sentence, convert_to_tensor = True)
scores = util.cos_sim(sentence_emb, emb)[0]


# Extend the output table's record capacity by the number of records in the input table
out_table.size = in_table.size

# Grab handles to the input & output table's columns
in_id = in_table['id']
in_sen = in_table['sentence']
out_id = out_table['id']
out_score = out_table['score']

# For each sentence in the input table,
# write the ID & distance score from the given sentence to the output table
for i in range(0, len(sentences)):

    # Copy the ID column data
    out_id[i] = in_id[i]

    # Set the distance score column data
    out_score[i] = scores[i]

proc_data.complete()
