"""
Read Tool - Reads files from the local filesystem
"""
import os
import mimetypes
import base64
import httpx
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Union
from io import BytesIO
from base_tool_handler import BaseToolHandler, ToolState, ToolFailedError
from tool_categories import ToolName

MAX_PDF_SIZE = 4 * 1024 * 1024 # 4MB
MAX_IMAGE_SIZE = 3 * 1024 * 1024 # 3MB

class ReadToolHandler(BaseToolHandler):
    """Tool for reading files from the local filesystem"""
    
    def __init__(self, tool_state: ToolState):
        super().__init__(tool_state=tool_state)
        
    @property
    def name(self) -> str:
        return ToolName.READ
    
    @property
    def display_result_type(self) -> str:
        return "read_result"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read, or HTTP URL for PDF/image files"
                },
                "offset": {
                    "type": "number",
                    "description": "The line number to start reading from. Only provide if the file is too large to read at once"
                },
                "limit": {
                    "type": "number", 
                    "description": "The number of lines to read. Only provide if the file is too large to read at once."
                }
            },
            "required": ["file_path"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
    
    def _is_http_url(self, path: str) -> bool:
        """Check if the path is an HTTP URL"""
        return path.startswith('http://') or path.startswith('https://')
    
    def _get_content_from_url(self, url: str) -> bytes:
        """Get content directly from HTTP URL without downloading to disk"""
        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Failed to fetch content from URL {url}: {str(e)}")
    
    def _validate_pdf(self, pdf_data: bytes, file_path: str) -> None:
        """
        Validate PDF file to detect corruption before sending to Claude.
        Raises ToolFailedError if PDF is invalid or corrupted.
        """
        try:
            # Try importing pypdf
            try:
                from pypdf import PdfReader
            except ImportError:
                # If pypdf is not available, try PyPDF2 as fallback
                try:
                    from PyPDF2 import PdfReader
                except ImportError:
                    # If no PDF library available, do basic validation
                    self._basic_pdf_validation(pdf_data, file_path)
                    return
            
            # Use pypdf/PyPDF2 to validate PDF structure
            try:
                pdf_stream = BytesIO(pdf_data)
                reader = PdfReader(pdf_stream, strict=True)
                
                # Try to access basic PDF properties to ensure it's readable
                num_pages = len(reader.pages)
                
                if num_pages == 0:
                    raise ToolFailedError(
                        f"PDF validation failed for {file_path}: PDF has 0 pages. "
                        "The file may be corrupted or incomplete."
                    )
                
                # Try to access the first page to ensure structure is valid
                _ = reader.pages[0]
                
            except Exception as e:
                error_msg = str(e)
                raise ToolFailedError(
                    f"PDF validation failed for {file_path}: {error_msg}\n"
                    "The PDF file appears to be corrupted or invalid. "
                    "Please verify the file integrity."
                )
                
        except ToolFailedError:
            # Re-raise ToolFailedError as-is
            raise
        except Exception as e:
            # Unexpected error during validation
            raise ToolFailedError(f"Error during PDF validation for {file_path}: {str(e)}")
    
    def _basic_pdf_validation(self, pdf_data: bytes, file_path: str) -> None:
        """
        Perform basic PDF validation without external libraries.
        Checks PDF header and basic structure.
        """
        if len(pdf_data) < 10:
            raise ToolFailedError(
                f"PDF validation failed for {file_path}: File is too small to be a valid PDF. "
                "The file may be corrupted or incomplete."
            )
        
        # Check PDF header (should start with %PDF-)
        header = pdf_data[:8]
        if not header.startswith(b'%PDF-'):
            raise ToolFailedError(
                f"PDF validation failed for {file_path}: Invalid PDF header. "
                "The file does not appear to be a valid PDF or is corrupted."
            )
        
        # Check for EOF marker (%%EOF should be near the end)
        # Look for %%EOF in the last 1024 bytes
        footer = pdf_data[-1024:]
        if b'%%EOF' not in footer:
            raise ToolFailedError(
                f"PDF validation failed for {file_path}: Missing PDF EOF marker. "
                "The file may be corrupted or incomplete."
            )
    
    def _validate_image(self, image_data: bytes, file_path: str) -> None:
        """
        Validate image file to detect corruption before sending to Claude.
        Raises ToolFailedError if image is invalid or corrupted.
        """
        try:
            # Try importing Pillow/PIL
            try:
                from PIL import Image
            except ImportError:
                # If PIL is not available, do basic validation
                self._basic_image_validation(image_data, file_path)
                return
            
            # Use PIL to validate image structure
            try:
                image_stream = BytesIO(image_data)
                img = Image.open(image_stream)
                
                # Verify the image by attempting to load it
                # This will raise an exception if the image is corrupted
                img.verify()
                
                # Re-open for additional checks (verify() closes the file)
                image_stream.seek(0)
                img = Image.open(image_stream)
                
                # Check basic properties
                if img.width <= 0 or img.height <= 0:
                    raise ToolFailedError(
                        f"Image validation failed for {file_path}: Invalid dimensions ({img.width}x{img.height}). "
                        "The image may be corrupted."
                    )
                
                # Try to get format
                if not img.format:
                    raise ToolFailedError(
                        f"Image validation failed for {file_path}: Unable to determine image format. "
                        "The image may be corrupted."
                    )
                
                # Check if format is supported by Claude
                supported_formats = ['JPEG', 'PNG', 'GIF', 'WEBP']
                if img.format.upper() not in supported_formats:
                    # This is a warning, not an error - let Claude decide
                    pass
                
            except ToolFailedError:
                # Re-raise our own errors
                raise
            except Exception as e:
                error_msg = str(e)
                raise ToolFailedError(
                    f"Image validation failed for {file_path}: {error_msg}\n"
                    "The image file appears to be corrupted or invalid. "
                    "Please verify the file integrity."
                )
                
        except ToolFailedError:
            # Re-raise ToolFailedError as-is
            raise
        except Exception as e:
            # Unexpected error during validation
            raise ToolFailedError(f"Error during image validation for {file_path}: {str(e)}")
    
    def _basic_image_validation(self, image_data: bytes, file_path: str) -> None:
        """
        Perform basic image validation without external libraries.
        Checks image file signatures (magic numbers).
        """
        if len(image_data) < 12:
            raise ToolFailedError(
                f"Image validation failed for {file_path}: File is too small to be a valid image. "
                "The file may be corrupted or incomplete."
            )
        
        # Check common image file signatures
        header = image_data[:12]
        
        # JPEG: FF D8 FF
        if header[:3] == b'\xff\xd8\xff':
            # Valid JPEG, check for EOI marker (FF D9) near the end
            if len(image_data) < 2:
                raise ToolFailedError(
                    f"Image validation failed for {file_path}: JPEG file is too small. "
                    "The file may be corrupted."
                )
            # Check last 2KB for EOI marker
            footer = image_data[-2048:] if len(image_data) > 2048 else image_data
            if b'\xff\xd9' not in footer:
                raise ToolFailedError(
                    f"Image validation failed for {file_path}: JPEG missing EOI marker. "
                    "The file may be corrupted or incomplete."
                )
            return
        
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            # Valid PNG signature, check for IEND chunk
            if b'IEND' not in image_data[-12:]:
                raise ToolFailedError(
                    f"Image validation failed for {file_path}: PNG missing IEND chunk. "
                    "The file may be corrupted or incomplete."
                )
            return
        
        # GIF: GIF87a or GIF89a
        if header[:6] in (b'GIF87a', b'GIF89a'):
            # Valid GIF signature
            return
        
        # WebP: RIFF....WEBP
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            # Valid WebP signature
            return
        
        # BMP: BM
        if header[:2] == b'BM':
            # Valid BMP signature
            return
        
        # If we get here, format is unknown or invalid
        raise ToolFailedError(
            f"Image validation failed for {file_path}: Unrecognized or invalid image format. "
            "Supported formats: JPEG, PNG, GIF, WebP, BMP. "
            "The file may be corrupted or not an image file."
        )
    
    def _extract_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """Read PDF file and return base64 data in Claude-compatible format"""
        try:
            # Read PDF as base64 for Claude
            if self._is_http_url(file_path):
                pdf_data = self._get_content_from_url(file_path)
            else:
                with open(file_path, 'rb') as f:
                    pdf_data = f.read()
            
            # Check file size
            pdf_size = len(pdf_data)
            if pdf_size > MAX_PDF_SIZE:
                raise ToolFailedError(
                    f"PDF file is too large: {pdf_size} bytes (max: {MAX_PDF_SIZE} bytes / {MAX_PDF_SIZE // (1024*1024)}MB). "
                )
            
            # Validate PDF before encoding to catch corruption early
            self._validate_pdf(pdf_data, file_path)
            
            base64_data = base64.standard_b64encode(pdf_data).decode('utf-8')
            
            return [{
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64_data
                }
            }]
            
        except Exception as e:
            raise ToolFailedError(f"Error reading PDF file {file_path}: {str(e)}")
    
    
    def _extract_image_info(self, file_path: str) -> Dict[str, Any]:
        """Read image file and return base64 data in Claude-compatible format"""
        try:
            # Read image as base64 for Claude
            if self._is_http_url(file_path):
                image_data = self._get_content_from_url(file_path)
            else:
                with open(file_path, 'rb') as f:
                    image_data = f.read()
            
            # Check file size
            image_size = len(image_data)
            if image_size > MAX_IMAGE_SIZE:
                raise ToolFailedError(
                    f"Image file is too large: {image_size} bytes (max: {MAX_IMAGE_SIZE} bytes / {MAX_IMAGE_SIZE // (1024*1024)}MB). "
                )
            
            # Validate image before encoding to catch corruption early
            self._validate_image(image_data, file_path)
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Get MIME type
            if self._is_http_url(file_path):
                # For URLs, try to guess from content or URL extension
                parsed_url = urlparse(file_path)
                url_path = parsed_url.path.lower()
                if url_path.endswith('.png'):
                    mime_type = 'image/png'
                elif url_path.endswith('.jpg') or url_path.endswith('.jpeg'):
                    mime_type = 'image/jpeg'
                elif url_path.endswith('.gif'):
                    mime_type = 'image/gif'
                elif url_path.endswith('.webp'):
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/jpeg'  # Default fallback
            else:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type or not mime_type.startswith('image/'):
                    mime_type = 'image/jpeg'  # Default fallback
            
            return [{
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64_data
                }
            }]
                
        except Exception as e:
            raise ToolFailedError(f"Error reading image file {file_path}: {str(e)}")

    async def execute_async(self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Execute the tool"""
        # Handle HTTP URLs
        if self._is_http_url(file_path):
            try:
                # For HTTP URLs, only support PDF and image files
                parsed_url = urlparse(file_path)
                url_path = parsed_url.path.lower()
                
                # Check if it's a PDF
                if url_path.endswith('.pdf'):
                    self.mark_file_as_read(file_path)
                    pdf_data = self._extract_pdf_content(file_path)
                    
                    return {
                        'tool_success': True,
                        'result': pdf_data,  # Agent gets the raw PDF data
                        'display_result': {
                            "content": [
                                {
                                    "type": "document",
                                    "path": file_path
                                }
                            ]
                        }
                    }
                
                # Check if it's an image
                if any(url_path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    self.mark_file_as_read(file_path)
                    image_data = self._extract_image_info(file_path)
                    
                    return {
                        'tool_success': True,
                        'result': image_data,  # Agent gets the raw image data
                        'display_result': {
                            "content": [
                                {
                                    "type": "image",
                                    "path": file_path
                                }
                            ]
                        }
                    }
                
                raise ToolFailedError(f"Error: HTTP URLs are only supported for PDF and image files. Got: {file_path}")
                
            except Exception as e:
                raise ToolFailedError(f"Error processing HTTP URL {file_path}: {str(e)}")
        
        # Validate absolute path for local files
        if not os.path.isabs(file_path):
            raise ToolFailedError(f"Error: file_path must be an absolute path, got: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise ToolFailedError(f"Error: File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ToolFailedError(f"Error: Path is not a file: {file_path}")
        
        try:
            # Check if it's a binary file type that we should handle specially
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Handle PDF files with base64 content
            if file_path.lower().endswith('.pdf'):
                self.mark_file_as_read(file_path)
                pdf_data = self._extract_pdf_content(file_path)
                
                return {
                    'tool_success': True,
                    'result': pdf_data,  # Agent gets the raw PDF data
                    'display_result': {
                        "content": [
                            {
                                "type": "document",
                                "path": file_path
                            }
                        ]
                    }
                }
            
            # Handle image files with base64 data
            if mime_type and mime_type.startswith('image/'):
                self.mark_file_as_read(file_path)
                image_data = self._extract_image_info(file_path)
                
                return {
                    'tool_success': True,
                    'result': image_data,  # Agent gets the raw image data
                    'display_result': {
                        "content": [
                            {
                                "type": "image",
                                "path": file_path
                            }
                        ]
                    }
                }
            
            # For Jupyter notebooks, provide info
            if file_path.lower().endswith('.ipynb'):
                file_size = os.path.getsize(file_path)
                raise ToolFailedError(f"Error: {file_path}\nFile size: {file_size} bytes\n\nNote: This is a Jupyter notebook. Use the NotebookRead tool instead for proper notebook reading.")
            
            # Read text file
            self.mark_file_as_read(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Handle empty file
            if not lines:
                agent_result = f"File is empty: {file_path}"
                
                return {
                    'tool_success': True,
                    'result': agent_result,
                    'display_result': {
                        "content": [
                            {
                                "type": "text",
                                "text": "File is empty."
                            }
                        ]
                    }
                }
            
            # Apply offset and limit
            start_line = (int(offset) - 1) if offset and int(offset) > 0 else 0
            end_line = start_line + int(limit) if limit else len(lines)
            
            # Ensure we don't go beyond file bounds
            # start_line = max(0, min(start_line, len(lines) - 1))
            if start_line >= len(lines):
                agent_result = f"<system-reminder>Warning: the file exists but is shorter than the provided offset ({offset}). The file has {len(lines)} lines.</system-reminder>"
                return {
                    'tool_success': True,
                    'result': agent_result,
                    'display_result': {
                        "content": [
                            {
                                "type": "text",
                                "text": "Read 0 lines"
                            }
                        ]
                    }
                }
            end_line = min(end_line, len(lines))
            
            # Apply default limit of 2000 lines if no limit specified
            if limit is None and offset is None:
                end_line = min(2000, len(lines))
            
            # Format output with line numbers (cat -n style)
            result_lines = []
            for i in range(start_line, end_line):
                line_num = i + 1
                line_content = lines[i].rstrip('\n\r')
                
                # Truncate long lines to 2000 characters
                if len(line_content) > 2000:
                    line_content = line_content[:2000] + "... [truncated]"
                
                # Format as cat -n style: proper spacing + line_num + tab + content
                spaces = " " * (6 - len(str(line_num)))
                result_lines.append(f"{spaces}{line_num}\t{line_content}")
            
            # Add info about truncation if applicable
            info_lines = []
            if start_line > 0:
                info_lines.append(f"[Showing lines {start_line + 1}-{end_line} of {len(lines)}]")
            
            if end_line < len(lines):
                remaining = len(lines) - end_line
                info_lines.append(f"[File has {remaining} more lines. Use offset and limit parameters to read more.]")

            # Mark file as read for other tools
            self.mark_file_as_read(file_path)
            
            # Combine info lines and content lines properly for agent result
            content_part = "\n".join(result_lines)
            if info_lines:
                info_part = "\n".join(info_lines)
                agent_result = info_part + "\n" + content_part
            else:
                agent_result = content_part
            
            # Prepare display content - just the file text without line numbers
            display_text_lines = []
            for i in range(start_line, end_line):
                line_content = lines[i].rstrip('\n\r')
                # Truncate long lines to 2000 characters
                if len(line_content) > 2000:
                    line_content = line_content[:2000] + "... [truncated]"
                display_text_lines.append(line_content)
            
            display_text = "\n".join(display_text_lines)
            
            return {
                'tool_success': True,
                'result': agent_result,
                'display_result': {
                    "content": [
                        {
                            "type": "text",
                            "text": display_text
                        }
                    ]
                }
            }
            
        except UnicodeDecodeError:
            # Handle binary files
            file_size = os.path.getsize(file_path)
            raise ToolFailedError(f"Binary file detected: {file_path}\nFile size: {file_size} bytes\n\nNote: This appears to be a binary file and cannot be read as text.")
        
        except PermissionError:
            raise ToolFailedError(f"Error: Permission denied reading file: {file_path}")

        except Exception as e:
            raise ToolFailedError(f"Error reading file {file_path}: {str(e)}")
        