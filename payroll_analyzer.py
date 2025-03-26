import streamlit as st
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from helpers import get_processed_output, analyze_multiple_documents

# Azure Document Intelligence Credentials
AZURE_ENDPOINT = os.getenv("AZURE_API_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_API_KEY")

@st.cache_resource
def get_client():
    return DocumentIntelligenceClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))

if __name__ == "__main__":

    client = get_client()

    ############## Streamlit UI ##############
    st.title("Payroll Processor")
    model_id = st.selectbox("Select a model", ["rina_string_content", "rulex-pre-2023-new", "rulex_new_2023-2024"])
    
    file_type = st.selectbox("Select file format", ["Excel", "CSV"])
    
    uploaded_files = st.file_uploader(
        "Upload a document", 
        type=["pdf", "jpg", "png", "jpeg"],
        accept_multiple_files=True
    )
    output = None

    if uploaded_files:
        if st.button("Process Document"):
            with st.spinner("Processing..."):
                result_df = analyze_multiple_documents(client, uploaded_files, model_id=model_id)
                
                st.write("### Extracted Key-Value Pairs")
                st.dataframe(result_df)

                output, mime_type, file_name = get_processed_output(
                    result_df, file_type
                )
        
        if output:
            st.download_button(
                label="Download Results",
                data=output.getvalue(),
                file_name=file_name,
                mime=mime_type
            )
