# Adobe_Forbidden
This repository contains the Docker-based solution for Challenge 1A of the Adobe India Hackathon.
The program processes PDF files and extracts a clean, structured outline from each document.

The output JSON for each PDF includes:
The document title (from PDF metadata or the largest text on the first page)
Headings classified as H1, H2, or H3
The page number where each heading appears
The solution removes decorative or non-informative elements such as separators, dotted lines, or boilerplate text.

How to Build and Run
Step 1: Place all PDF files to be processed in the input folder.
Step 2: Build the Docker image:
docker build --platform linux/amd64 -t adobe-solution .
Step 3: Run the container:
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none adobe-solution
Step 4: The JSON results for each PDF will be available in the output folder, named with the same base name as the PDF.

Example
If you place file02.pdf in the input folder, after running the container, a JSON file called file02.json will appear in the output folder with the extracted title, H1, H2, and H3 headings, and the page numbers.


The program uses PyMuPDF for PDF text extraction.
Headings are classified based on a combination of font size percentile, bold or uppercase styling, and text patterns such as numbering or common heading keywords.
The container runs entirely offline and processes up to 50 pages per PDF in under 10 seconds on CPU.

