import os
import wikipedia
import argparse
import re
from urllib.parse import urlparse
import requests

from openai import OpenAI

def get_wiki_page(topic):
    try:
        page = wikipedia.page(topic)
    except wikipedia.exceptions.DisambiguationError as e:
        print("Disambiguation error: ", e.options)
        return None
    except wikipedia.exceptions.PageError:
        print(f"Page not found for the topic: {topic}")
        return None
    return page

def download_image(url, folder = "./"):
    """Download an image and save it to a local folder."""
    excludes = [ "Commons-logo.svg" ]
    image_name = os.path.basename(urlparse(url).path)
    if image_name not in excludes:
        image_path = os.path.join(folder, image_name)
        if not os.path.isfile(image_path):
            response = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64"})
            if response.status_code == 200:
                with open(image_path, 'wb') as file:
                    file.write(response.content)
                return image_name
            else:
                print(f"Response for {url} was: {response.status_code}!")
        else:
            print(f"Image {image_name} already downloaded.")
            return image_name
    else:
        print(f"Image {image_name} excluded.")
    return None

def page_to_markdown_images(page, folder = "./"):
    markdown = ""
    for image in page.images:
        print(f"Processing image {image}...")
        path = download_image(image, folder)
        if (path):
            markdown += f"![[{path}]]\n"
        else:
            print(f"Image {image} failed to download!")
    return markdown

def apply_prompt_to_markdown(prompt, markdown):
    prompt += markdown
 
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}])

    return response.choices[0].message.content

# FIXME: unreliable prompt
def markdown_remove_excludes(markdown):
    excludes = ["Jegyzetek", "További információk", "Kapcsolódó szócikkek"]
    excludes_text = ""
    for exclude in excludes:
        excludes_text += f"{exclude}, "
    
    prompt = """
    You'll be given a markdown text, remove the headers (and their content) that are called: {excludes_text}\n
    Only return the output text, here's the input text:\n
    """

    return apply_prompt_to_markdown(prompt, markdown)

def fix_latex_in_markdown(markdown):
    prompt = """
    Proper LaTeX syntax for markdown is $latex expression$ for inline, and $$latex expression$$ for a block.
    Our conversion made some mistakes with it, and math notations are all over the place.
    Return it with the aforementioned proper syntax (decide if inline (like if it's a number and part of the text) or a block (for longer and more standalone equations) will look better), and write nothing more. Here's the text:\n
    """

    return apply_prompt_to_markdown(prompt, markdown)

def page_to_markdown(page):
    markdown = ""
    
    content = page.content

    content = re.sub(r"=== ([^=]+) ===", r"### \1", content)  # Subsections
    content = re.sub(r"== ([^=]+) ==", r"## \1", content)   # Main sections
    content = re.sub(r"^= ([^=]+) =", r"# \1", content)     # Top-level header

    content = re.sub(r"(?<=\n)(## .*)(?=\n)", r"\n\1\n", content)
    content = re.sub(r"(?<=\n)(### .*)(?=\n)", r"\n\1\n", content)

    markdown += content

    return markdown

def text_to_file(text, name, folder = "./"):
    path = os.path.join(folder, name)
    with open(path, 'w') as file:
        file.write(text)
    return path



parser = argparse.ArgumentParser(
    description="Generate a markdown file for a provided topic."
)
parser.add_argument(
    "topic",
    type=str,
    help="The topic to generate a markdown file for.",
)
parser.add_argument(
    "--lang",
    type=str,
    default="hu",
    help="The language of Wikipedia to use.",
)
parser.add_argument(
    "--root",
    type=str,
    default="hu",
    help="Where to store article and images.",
)
args = parser.parse_args()

wikipedia.set_lang(args.lang)

page = get_wiki_page(args.topic)

markdown = page_to_markdown(page)
#markdown = markdown_remove_excludes(markdown)
markdown = fix_latex_in_markdown(markdown)
markdown += f"\n{page_to_markdown_images(page, args.root)}"

path = text_to_file(markdown, f"{args.topic}.md", args.root)
print(f"Article saved to: {path}")
