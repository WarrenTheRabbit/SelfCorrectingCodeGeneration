from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from bs4 import BeautifulSoup as Soup

def retrieve_docs(debug: bool = True):
    if debug:
        return "A document"
    
    url = "https://python.langchain.com/docs/expression_language/"
    loader = RecursiveUrlLoader(
        url=url,
        max_depth=20,
        extractor=lambda x: Soup(x, "html.parser").text,
    )
    docs = loader.load()
    docs_sorted = (
        sorted(docs, key=lambda x: x.metadata["source"])
    )
    docs_reversed = list(reversed(docs_sorted))
    
    docs_as_string = "\n\n------\n\n".join(document.page_content
                                           for document 
                                           in docs_reversed)
    
    with open("data/lcel.txt", "w") as file:
        file.write(docs_as_string)
        
    return docs_as_string[:100]
    
    
    