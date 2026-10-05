import base64
import io
import uuid
from urllib.parse import quote

import boto3
import httpx
from PIL import Image, ImageDraw
from langchain_core.tools import tool

from app.config import get_settings

ASPECT_SIZE = {
    "instagram": "1024x1024",
    "telegram": "1024x1024",
    "linkedin": "1536x1024",
    "twitter": "1536x1024",
    "facebook": "1536x1024",
    "youtube": "1536x1024",
    "tiktok": "1024x1536",
}

PROMPT_SUFFIX = (
    "professional product photography, high quality, social media advertisement, "
    "elegant composition, no text, no watermark"
)


def _s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        region_name=s.aws_region,
        aws_access_key_id=s.aws_access_key_id or "minioadmin",
        aws_secret_access_key=s.aws_secret_access_key or "minioadmin",
    )


def upload_bytes(data: bytes, key: str, content_type: str = "image/png") -> str:
    s = get_settings()
    client = _s3_client()

    try:
        client.create_bucket(Bucket=s.aws_s3_bucket)
    except Exception:
        pass

    client.put_object(
        Bucket=s.aws_s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    base = s.s3_public_base_url or f"https://{s.aws_s3_bucket}.s3.{s.aws_region}.amazonaws.com"
    return f'{base.rstrip("/")}/{key}'


def _placeholder(prompt: str) -> bytes:
    img = Image.new("RGB", (1024, 1024), color=(245, 245, 245))
    d = ImageDraw.Draw(img)

    d.text((50, 50), "AI Campaign Image Placeholder", fill=(10, 10, 10))
    d.text((50, 100), prompt[:600], fill=(30, 30, 30))

    buff = io.BytesIO()
    img.save(buff, format="PNG")
    return buff.getvalue()


def _build_image_prompt(image_prompt: str) -> str:
    prompt = (image_prompt or "marketing campaign image").strip()
    return f"{prompt}, {PROMPT_SUFFIX}"


def _extension_for_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }

    clean_type = (content_type or "image/png").split(";", 1)[0].strip().lower()
    return mapping.get(clean_type, "png")


async def _generate_openai_image(
    client: httpx.AsyncClient,
    prompt: str,
    platform: str,
    api_key: str,
) -> tuple[bytes, str]:
    size = ASPECT_SIZE.get(platform, "1024x1024")

    response = await client.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-image-1",
            "prompt": prompt,
            "n": 1,
            "size": size,
        },
    )

    if response.status_code >= 400:
        print(
            "OpenAI image generation failed; falling back to placeholder. "
            f"status={response.status_code} body={response.text[:500]}"
        )
        return _placeholder(prompt), "image/png"

    data = response.json().get("data", [{}])[0]

    if data.get("url"):
        img_response = await client.get(data["url"])

        if img_response.status_code >= 400:
            print(
                "OpenAI generated image URL download failed; falling back to placeholder. "
                f"status={img_response.status_code} body={img_response.text[:500]}"
            )
            return _placeholder(prompt), "image/png"

        return img_response.content, img_response.headers.get("content-type", "image/png")

    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"]), "image/png"

    print("OpenAI image response did not include url or b64_json; falling back to placeholder.")
    return _placeholder(prompt), "image/png"


async def _generate_pollinations_image(
    client: httpx.AsyncClient,
    prompt: str,
) -> tuple[bytes, str]:
    response = await client.get(
        f"https://image.pollinations.ai/prompt/{quote(prompt, safe='')}"
    )

    content_type = response.headers.get("content-type", "")

    if response.status_code != 200:
        raise ValueError(f"Pollinations returned status {response.status_code}")

    if not content_type.lower().startswith("image/"):
        raise ValueError(f"Pollinations returned non-image content type: {content_type}")

    if len(response.content) <= 1000:
        raise ValueError("Pollinations returned an unexpectedly small payload")

    return response.content, content_type


async def generate_image(image_prompt: str, platform: str) -> str:
    s = get_settings()

    raw_prompt = image_prompt or "marketing campaign image"
    prompt = _build_image_prompt(raw_prompt)
    provider = (s.image_provider or "placeholder").lower()

    if provider == "placeholder":
        key = f"generated/{uuid.uuid4()}.png"
        return upload_bytes(_placeholder(raw_prompt), key)

    async with httpx.AsyncClient(timeout=120) as client:
        if provider == "openai":
            if not s.openai_api_key:
                print("OPENAI_API_KEY missing; falling back to placeholder.")
                key = f"generated/{uuid.uuid4()}.png"
                return upload_bytes(_placeholder(raw_prompt), key)

            try:
                image_bytes, content_type = await _generate_openai_image(
                    client=client,
                    prompt=prompt,
                    platform=platform,
                    api_key=s.openai_api_key,
                )

                key = f"generated/{uuid.uuid4()}.{_extension_for_content_type(content_type)}"
                return upload_bytes(image_bytes, key, content_type=content_type)

            except Exception as exc:
                print(f"OpenAI image generation exception; falling back to placeholder. error={exc}")
                key = f"generated/{uuid.uuid4()}.png"
                return upload_bytes(_placeholder(raw_prompt), key)

        if provider == "pollinations":
            try:
                image_bytes, content_type = await _generate_pollinations_image(
                    client=client,
                    prompt=prompt,
                )

                key = f"generated/{uuid.uuid4()}.{_extension_for_content_type(content_type)}"
                return upload_bytes(image_bytes, key, content_type=content_type)

            except Exception as exc:
                print(f"Pollinations image generation failed; falling back to placeholder. error={exc}")
                key = f"generated/{uuid.uuid4()}.png"
                return upload_bytes(_placeholder(raw_prompt), key)

    print(f"Unknown IMAGE_PROVIDER={provider}; falling back to placeholder.")
    key = f"generated/{uuid.uuid4()}.png"
    return upload_bytes(_placeholder(raw_prompt), key)


@tool("media_gen_tool")
def media_gen_tool(image_prompt: str, platform: str = "instagram") -> str:
    """Generate an image from a prompt and return an S3/MinIO URL."""
    import asyncio

    return asyncio.run(generate_image(image_prompt, platform))