import requests
from shared.composio_tools.lib.tool import Tool,Action
from pydantic import BaseModel, Field
from typing import Optional, Dict
from fastapi import UploadFile, File



class CreateDocumentRequest(BaseModel):
    title: Optional[str] = Field(None, description="Title of the new Google Docs document")
    text: Optional[str] = Field(None, description="Initial text to insert into the document")

class CreateDocumentResponse(BaseModel):
    
    document_details: dict = Field(None, description="Details of the newly created document")

class CreateDocument(Action):
    """
    Creates a new Google Docs document with an optional title and text.
    """
    
    @property
    def display_name(self) -> str:
        return "Create Document"

    @property
    def request_schema(self) -> BaseModel:
        return CreateDocumentRequest
    
    @property
    def response_schema(self) -> BaseModel:
        return CreateDocumentResponse

    def execute(self, req: CreateDocumentRequest, authorisation_data: Dict) -> CreateDocumentResponse:
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get("base_url", "https://docs.googleapis.com")
            create_url = f"{base_url}/v1/documents"

            # Create a new document
            document_response = requests.post(create_url, headers=headers, json={"title": req.title})
            if document_response.status_code != 200:
                return CreateDocumentResponse(success=False)

            document = document_response.json()
            document_id = document.get('documentId')

            # If text is provided, insert it into the document
            if req.text:
                update_url = f"{base_url}/v1/documents/{document_id}:batchUpdate"
                requests_body = {
                "title": req.title,
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {
                                        "textRun": {
                                            "content": req.text
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
                response = requests.post(update_url, headers=headers, json=requests_body)
                if response.status_code == 200:
                 return {
                    "execution_details": {"executed": True},
                    "response_data": {"success": response.json()},
                }
                else:
                 return {
                    "execution_details": {"executed": False},
                    "response_data": {"success": response.json()}
                }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "error": str(e)},
            }



class AppendTextToDocumentRequest(BaseModel):
    document_id: str = Field(
        ...,
        description="The unique identifier of the Google Docs document to which the text will be appended. This ID can be extracted from the document's URL or using Google Drive API.",
        example="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    )
    text_to_append: str = Field(
        ...,
        description="The plain text to append to the document.",
        example="This is some text that will be appended."
    )

class AppendTextToDocumentResponse(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the text was successfully appended"
    )


class AppendTextToDocument(Action):
    """
    Appends text to an existing document in Google Docs.
    """

    @property
    def display_name(self) -> str:
        return "Append Text to Document"

    @property
    def request_schema(self) -> BaseModel:
        return AppendTextToDocumentRequest

    @property
    def response_schema(self) -> BaseModel:
        return AppendTextToDocumentResponse
    
    def create_style_requests(self, text_style, text_length: int):
        style_requests = []

        if text_style.bold is not None:
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": text_length + 1},
                    "textStyle": {"bold": text_style.bold},
                    "fields": "bold"
                }
            })

        if text_style.italic is not None:
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": text_length + 1},
                    "textStyle": {"italic": text_style.italic},
                    "fields": "italic"
                }
            })

        if text_style.underline is not None:
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": text_length + 1},
                    "textStyle": {"underline": text_style.underline},
                    "fields": "underline"
                }
            })

        if text_style.font_size is not None:
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": text_length + 1},
                    "textStyle": {
                        "fontSize": {"magnitude": text_style.font_size, "unit": "PT"}
                    },
                    "fields": "fontSize"
                }
            })

        return style_requests


    def execute(self, req: AppendTextToDocumentRequest, authorisation_data: dict, text_length: int):
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get(
                "base_url", "https://docs.googleapis.com"
            )
            url = f"{base_url}/v1/documents/{req.document_id}:batchUpdate"

            # Prepare the request body to append text to the document
            data = {
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": req.text_to_append,
                        }
                    }
                ]
            }
            if req.text_style:
                style_requests = self.create_style_requests(req.text_style, text_length)
                data['requests'].extend(style_requests)

            # Send the request to append text
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                return {
                    "execution_details": {"executed": True},
                    "response_data": {"success": response.json()},
                }
            else:
                return {
                    "execution_details": {"executed": False},
                    "response_data": {"success": response.json()}
                }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "error": str(e)},
            }

    

class CreateDocumentFromTemplateRequest(BaseModel):
    template_document_id: str = Field(
        ..., description="ID of the template document to create a new document from"
    )
    replacements: Dict[str, str] = Field(
        ..., description="Dictionary of placeholder variables and their replacements"
    )
    new_document_title: str = Field(
        "New Document", description="Title of the new document to be created"
    )


class CreateDocumentFromTemplateResponse(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the new document creation was successful"
    )
    new_document: str = Field(
        None, description="ID of the newly created document if successful"
    )


class CreateDocumentFromTemplate(Action):
    """
    Create a new document based on a template document and replace placeholder variables.
    """

    @property
    def display_name(self) -> str:
        return "Create Document from Template"

    @property
    def request_schema(self) -> BaseModel:
        return CreateDocumentFromTemplateRequest

    @property
    def response_schema(self) -> BaseModel:
        return CreateDocumentFromTemplateResponse

    def execute(
        self, req: CreateDocumentFromTemplateRequest, authorisation_data: dict
    ) -> dict:
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get(
                "base_url", "https://docs.googleapis.com"
            )
            url = f"{base_url}/v1/documents/{req.template_document_id}:copy"

            # Prepare the request body to copy the template document
            data = {
                "title": req.new_document_title,  # Set the title for the new document
            }

            # Send the request to copy the template document
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                new_document = response.json()
                # Replace placeholder variables in the new document
                if new_document:
                    success = self.replace_placeholders(
                        new_document, req.replacements, headers
                    )
                    if success:
                        return {
                            "execution_details": {"executed": True},
                            "response_data": {"success": True, "new_document": new_document},
                        }
                    else:
                        return {
                            "execution_details": {"executed": False},
                            "response_data": {"success": False, "new_document": new_document},
                        }
                else:
                    return {
                        "execution_details": {"executed": False},
                        "response_data": {"success": False, "new_document": new_document},
                    }
            else:
                return {
                    "execution_details": {"executed": False},
                    "response_data": {"success": False, "new_document": new_document},
                }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "document_id": "", "error": str(e)},
            }
        
    
   

    def replace_placeholders(self, new_document: dict, replacements: Dict[str, str], headers: dict) -> bool:
        base_url = "https://docs.googleapis.com"
        document_id = new_document.get('documentId')
        url = f"{base_url}/v1/documents/{document_id}:batchUpdate"
        requests_list = []

        # Create requests for each replacement
        for placeholder, replacement in replacements.items():
            # Find the placeholder in the document and replace it
            # This is a simplified example. You may need to implement a more robust search and replace logic
            requests_list.append({
                "replaceAllText": {
                    "containsText": {
                        "text": placeholder,
                        "matchCase": True
                    },
                    "replaceText": replacement,
                }
            })

        # Prepare the request body with all replacement requests
        data = {
            "requests": requests_list
        }

        # Send the request to make the replacements
        response = requests.post(url, headers=headers, json=data)

        # Check if the replacements were successful
        return response.status_code == 200
        

class UploadDocumentRequest(BaseModel):
    file_name: Optional[str] = Field(None, description="Name to assign to the uploaded file in Google Docs")


class UploadDocumentResponse(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the document was successfully uploaded"
    )
    document_id: Optional[str] = Field(None, description="ID of the uploaded document in Google Docs")


class UploadDocument(Action):
    """
    Uploads a document to Google Docs.
    """

    @property
    def display_name(self) -> str:
        return "Upload Document"

    @property
    def request_schema(self) -> BaseModel:
        return UploadDocumentRequest

    @property
    def response_schema(self) -> BaseModel:
        return UploadDocumentResponse

    def execute(self, req: UploadDocumentRequest, authorisation_data: dict, file: UploadFile = File(...)):
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get("base_url", "https://docs.googleapis.com")
            upload_url = f"{base_url}/v1/documents:upload"

            # Read the uploaded file
            file_content = file.file.read()

            # Prepare the request body to upload the document
            data = {
                "content": file_content.decode("utf-8"),
                "fileName": req.file_name,
            }

            # Send the request to upload the document
            response = requests.post(upload_url, headers=headers, json=data)

            if response.status_code == 200:
                return {
                    "execution_details": {"executed": True},
                    "response_data": {"success": True, "document_id": response.json().get("id")},
                }
            else:
                return {
                    "execution_details": {"executed": False},
                    "response_data": {"success": False, "document_id": None},
                }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "document_id": None, "error": str(e)},
            }



class CreateDocumentFromTextRequest(BaseModel):
    document_content: str = Field(..., description="Content of the document to create. Limited HTML is supported.")
    title: str = Field(..., description="Title of the document")


class CreateDocumentFromTextResponse(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the document creation was successful"
    )
    document_id: str = Field(None, description="ID of the created document")


class CreateDocumentFromText(Action):
    """
    Create a new document from text. Limited HTML is supported.
    """

    @property
    def display_name(self) -> str:
        return "Create Document from Text"

    @property
    def request_schema(self) -> BaseModel:
        return CreateDocumentFromTextRequest

    @property
    def response_schema(self) -> BaseModel:
        return CreateDocumentFromTextResponse

    def execute(self, req: CreateDocumentFromTextRequest, authorisation_data: dict):
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get(
                "base_url", "https://docs.googleapis.com"
            )
            url = f"{base_url}/v1/documents"

            # Prepare the request body to create a new document from text
            data = {
                "title": req.title,
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {
                                        "textRun": {
                                            "content": req.document_content
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }

            # Send the request to create the document
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                document_id = response.json().get("id")
                return {
                    "execution_details": {"executed": True},
                    "response_data": {"success": True, "document_id": document_id},
                }
            else:
                return {
                    "execution_details": {"executed": False},
                    "response_data": {"success": False, "document_id": None},
                }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "document_id": None, "error": str(e)},
            }
        


class FindOrCreateDocumentRequest(BaseModel):
    document_title: str = Field(..., description="Title of the document to find or create")


class FindOrCreateDocumentResponse(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the operation was successful"
    )
    document_id: str = Field(None, description="ID of the found or created document")


class FindOrCreateDocument(Action):
    """
    Finds or creates a specific document.
    """

    @property
    def display_name(self) -> str:
        return "Find or Create Document"

    @property
    def request_schema(self) -> BaseModel:
        return FindOrCreateDocumentRequest

    @property
    def response_schema(self) -> BaseModel:
        return FindOrCreateDocumentResponse

    def execute(self, req: FindOrCreateDocumentRequest, authorisation_data: dict):
        try:
            headers = authorisation_data.get("headers", {})
            base_url = authorisation_data.get(
                "base_url", "https://docs.googleapis.com"
            )

            # Check if the document exists
            document_id = self.find_document(req.document_title, headers, base_url)

            if document_id:
                return {
                    "execution_details": {"executed": True},
                    "response_data": {"success": True, "document_id": document_id},
                }
            else:
                # If the document does not exist, create a new one
                new_document_id = self.create_document(req.document_title, headers, base_url)
                if new_document_id:
                    return {
                        "execution_details": {"executed": True},
                        "response_data": {"success": True, "document_id": new_document_id},
                    }
                else:
                    return {
                        "execution_details": {"executed": False},
                        "response_data": {"success": False, "document_id": None},
                    }

        except Exception as e:
            return {
                "execution_details": {"executed": False},
                "response_data": {"success": False, "document_id": None, "error": str(e)},
            }

    def find_document(self, title: str, headers: dict, base_url: str) -> str:
        # Query the API to find the document by title
        url = f"{base_url}/v1/documents"
        params = {"title": title}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            documents = response.json().get("documents", [])
            if documents:
                return documents[0].get("id")
        return ""

    def create_document(self, title: str, headers: dict, base_url: str) -> str:
        # Prepare the request body to create a new document
        data = {"title": title}
        url = f"{base_url}/v1/documents"

        # Send the request to create the document
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            return response.json().get("id")
        return ""




        

    





class GoogleDocs3(Tool):
    """
    Connect to Google Docs to perform various document-related actions.
    """

    def actions(self) -> list:
        return [
                AppendTextToDocument,
                CreateDocumentFromTemplate,
                UploadDocument,
                CreateDocumentFromText,
                FindOrCreateDocument,
                CreateDocument,
               ]

    def triggers(self) -> list:
        return []


__all__ = ["GoogleDocs3"]
