# SmartDoc Finder

## 🧠 Inspiration
Organizations have countless documents manuals, policies, PDFs but finding the right information quickly can be challenging. SmartDoc Finder was created to turn static documents into an interactive, intelligent knowledge base.

## 💬 What it does
SmartDoc Finder is an AI-powered chatbot that allows users to ask natural language questions and receive precise answers from company documents. It uses **Elastic Search** to find relevant text snippets and **Google Vertex AI (Gemini)** to generate clear, context-aware responses with links to sources.

## 🛠️ How we built it
- **Backend**: Python + FastAPI  
- **Frontend**: simple chat interface using HTML/JS or Streamlit  
- **Database / Search**: Elastic Search for indexing documents  
- **AI**: Google Vertex AI (Gemini) for generating answers  
- **Document Parsing**: PyPDF2 for PDF text extraction  
- **Hosting**: Google Cloud Run (backend) + static frontend  

## 🚧 Challenges we ran into
- Configuring Elastic Search for multilingual document search  
- Ensuring accuracy of AI-generated answers  
- Securely integrating Elastic Search with Vertex AI  
- Optimizing performance with large document collections  

## 🏆 Accomplishments we're proud of
- Successful integration of Elastic Search + Gemini (RAG workflow)  
- Fully functional end-to-end chatbot  
- Multi-language support with source references  
- Clean and intuitive user interface  

## 📚 What we learned
- Building a **Retrieval-Augmented Generation (RAG)** workflow  
- Effective use of Elastic Search and Vertex AI  
- Prompt engineering for AI based on source documents  
- Importance of clear UX in technical projects  

## 🚀 What's next
- Add user authentication and personalized document access  
- Support more file formats (Word, Confluence, Google Drive)  
- Improve scalability for thousands of documents  
- Build analytics for user questions and knowledge gaps  
- Deploy as a plug-and-play tool for companies  

## 🛠️ Tools & Technologies
- Python, FastAPI, Uvicorn  
- Elastic Search  
- Google Vertex AI (Gemini)  
- PyPDF2, Pandas  
- HTML/JS (frontend)  
- Google Cloud Run  
