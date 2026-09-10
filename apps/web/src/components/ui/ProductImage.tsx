"use client";

type ProductImageProps = {
  name: string;
  className?: string;
  alt?: string;
};

const OATS_IMAGE =
  "https://upload.wikimedia.org/wikipedia/commons/e/e1/USDA_2026_Oats_bowl.png";
const RICE_IMAGE =
  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/White_Rice_03.jpg/960px-White_Rice_03.jpg";
const LENTILS_IMAGE =
  "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Lentil.jpg/960px-Lentil.jpg";
const JAMESON_IMAGE =
  "https://ik.imagekit.io/cvygf2xse/jamesonwhiskey/wp-content/uploads/2026/03/Jameson-Original-Cropped-1.png?tr=q-80%2Cw-151";

function resolveProductImage(name: string): string | null {
  const normalized = name.toLocaleLowerCase();

  if (
    normalized.includes("галич") ||
    normalized.includes("butter") ||
    normalized.includes("масло")
  ) {
    return "/butter-galychyna.png";
  }

  if (
    normalized.includes("jameson") ||
    normalized.includes("whiskey") ||
    normalized.includes("whisky") ||
    normalized.includes("віскі")
  ) {
    return JAMESON_IMAGE;
  }

  if (
    normalized.includes("oat") ||
    normalized.includes("овес") ||
    normalized.includes("вівся")
  ) {
    return OATS_IMAGE;
  }

  if (normalized.includes("rice") || normalized.includes("рис")) {
    return RICE_IMAGE;
  }

  if (
    normalized.includes("lentil") ||
    normalized.includes("сочев") ||
    normalized.includes("чечев")
  ) {
    return LENTILS_IMAGE;
  }

  return null;
}

export function ProductImage({
  name,
  className = "h-10 w-12",
  alt,
}: ProductImageProps) {
  const src = resolveProductImage(name);

  if (!src) {
    return (
      <div
        className={`${className} flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-[#E8EBF0] bg-[#F7F9FA]`}
        role="img"
        aria-label={alt ?? name}
      >
        <div className="relative h-5 w-8 rounded-sm bg-white shadow-sm">
          <span className="absolute bottom-1 left-0 h-1 w-full bg-[#F89F46]" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${className} flex shrink-0 items-center justify-center overflow-hidden`}
    >
      <img
        src={src}
        alt={alt ?? name}
        className="max-h-full max-w-full object-contain"
      />
    </div>
  );
}
