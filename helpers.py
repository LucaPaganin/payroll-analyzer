import re
import time
import streamlit as st
import pandas as pd
import io
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import DocumentAnalysisFeature, AnalyzeResult

FLOAT_REGEX = re.compile(r"[\d,\.]+")
        
def analyze_multiple_documents(client: DocumentIntelligenceClient, files: list, model_id: str):
    series = []
    for f in files:
        print(f"Working on file {f.name}")
        single_series = analyze_document(client, f.getvalue(), model_id)
        series.append(single_series)
    
    res_df = pd.concat(series, axis=1).T
    
    return res_df




def analyze_document(client: DocumentIntelligenceClient, file, model_id: str):
    """Process document using Azure Document Intelligence"""
    try:
        print(f"Start analyzing single file")
        t0 = time.time()
        poller = client.begin_analyze_document(
            model_id, 
            file
        )
        result = poller.result()
        print(f"document analyzed in {time.time() - t0:.2f} seconds")
        key_value_pairs = {}
        
        if result.documents:
            for idx, document in enumerate(result.documents):
                t0 = time.time()
                print(f"--------Analyzing document #{idx + 1}--------")
                print(f"Document has type {document.doc_type}")
                print(f"Document has document type confidence {document.confidence}")
                print(f"Document was analyzed with model with ID {result.model_id}")
                if document.fields:
                    for name, field in document.fields.items():
                        if (valuestring := field.get("valueString")) is not None:
                            print(
                                f"......found field '{name}' with value '{valuestring}' and with confidence {field.confidence}"
                            )
                            value = valuestring
                            if FLOAT_REGEX.match(valuestring):
                                value = cast_to_float(valuestring)
                            key_value_pairs[name] = value
                        else:
                            value_object = field.get("valueObject")
                            if value_object:
                                print(
                                    f"......found object field '{name}' with confidence {field.confidence}"
                                )
                                field_values = flatten_table_dict(value_object, prefix=f"{name}_")
                                new_field_values = {
                                    k: cast_to_float(v) if v and FLOAT_REGEX.match(v) else v
                                    for k, v in field_values.items()
                                }
                                key_value_pairs.update(new_field_values)
                
                print(f"--------Finished analyzing document #{idx + 1}--------")
        
        return pd.Series(key_value_pairs)

    except Exception as e:
        st.error(f"An error occurred: {e}")


def get_processed_output(processed_series: pd.Series, file_type: str):
    output = io.BytesIO()

    if file_type == "CSV":
        processed_series.to_csv(output, index=True)
        mime_type = "text/csv"
        file_name = "processed_data.csv"
    else:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            processed_series.to_excel(writer)
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_name = "processed_data.xlsx"
    
    return output, mime_type, file_name

def cast_to_float(s: str, thousands_sep=".", decimal_sep=","):
    match = FLOAT_REGEX.match(s)
    if not match:
        raise ValueError(f"cannot cast string '{s}' to float")
    res = match.group().replace(thousands_sep, "").replace(decimal_sep, ".")
    return float(res)


############################################################################
def _in_span(word, spans):
    for span in spans:
        if word.span.offset >= span.offset and (word.span.offset + word.span.length) <= (span.offset + span.length):
            return True
    return False

def _format_bounding_region(bounding_regions):
    if not bounding_regions:
        return "N/A"
    return ", ".join(
        f"Page #{region.page_number}: {_format_polygon(region.polygon)}" for region in bounding_regions
    )

def _format_polygon(polygon):
    if not polygon:
        return "N/A"
    return ", ".join([f"[{polygon[i]}, {polygon[i + 1]}]" for i in range(0, len(polygon), 2)])

def flatten_table_dict(d, prefix=""):
    """Recursively flattens a nested dictionary."""
    res = {}
    for k1, v1 in d.items():
        tmp = v1["valueObject"]
        for k2, v2 in tmp.items():
            res[f"{prefix}{k1}_{k2}"] = v2.get("valueString")
    return res