import json
import pdfplumber
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extraire le texte d'un PDF en utilisant pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Erreur lors de la lecture du PDF {pdf_path}: {e}")
    return text

def extract_specs_from_text(text: str) -> dict:
    """Utilise l'agent LLM (Mistral) pour extraire les spécifications techniques au format JSON."""
    llm = ChatOllama(model="mistral", temperature=0)

    prompt_template = """
    Tu es un expert en ingénierie mécanique. Analyse le texte technique suivant extrait d'un plan PDF
    et extrais les spécifications clés au format JSON stricte. 
    
    Les informations à extraire (si présentes) :
    - diametre_nominal
    - pression_nominale
    - materiau
    - longueur_face_a_face
    - tolerance
    - norme
    
    Texte technique :
    {text}
    
    Réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte avant ou après. 
    Si une information n'est pas trouvée, mets "Non spécifié".
    Exemple de sortie :
    {{
        "diametre_nominal": "DN100",
        "pression_nominale": "PN40",
        "materiau": "Inox 316L",
        "longueur_face_a_face": "229mm",
        "tolerance": "±0.1mm",
        "norme": "EN 558"
    }}
    """
    
    prompt = PromptTemplate(input_variables=["text"], template=prompt_template)
    chain = prompt | llm
    
    response = chain.invoke({"text": text})
    
    try:
        # Nettoyage si le LLM renvoie des balises Markdown (ex: ```json ... ```)
        cleaned_response = response.content.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
            
        specs_json = json.loads(cleaned_response.strip())
        return specs_json
    except json.JSONDecodeError:
        print("Erreur : La réponse du LLM n'est pas un JSON valide.")
        print("Réponse brute :", response.content)
        return {"error": "JSON invalide", "raw_response": response.content}

def process_pdf(pdf_path: str) -> dict:
    """Fonction principale pour lire le PDF et retourner les spécifications JSON."""
    print(f"Extraction du texte depuis {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text.strip():
        return {"error": "Aucun texte n'a pu être extrait du PDF."}
         
    print("Analyse du texte par le LLM (Mistral)...")
    specs = extract_specs_from_text(text)
    return specs

if __name__ == "__main__":
    import sys
    import os
    
    # Par défaut, utiliser le PDF de test fourni si aucun argument n'est passé
    default_pdf = os.path.join(os.path.dirname(__file__), "pdfs_test", "vanne_industrielle_DN100.pdf")
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else default_pdf
    
    result = process_pdf(pdf_file)
    print("\n----- Résultat Extraction JSON -----")
    print(json.dumps(result, indent=4, ensure_ascii=False))
