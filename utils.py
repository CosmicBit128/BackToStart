import pygame as pg


# Load an image
def load_img(image: str | pg.Surface, crop: None | tuple[int, int, int, int] = None, ratio: tuple[int, int] = (4, 4)) -> pg.Surface:
    """
    Loads an image from a file or a Pygame Surface, optionally crops it, and resizes it by a factor.
    
    Parameters:
    image (str or pygame.Surface): The file path to the image or a Pygame Surface object.
    crop (tuple, optional): A tuple (x, y, width, height) defining the crop area. Defaults to None.
    ratio (tuple or float): A tuple (width_factor, height_factor) or a single float for uniform scaling. Defaults to (2, 2).

    Returns:
    pygame.Surface: The processed Pygame Surface object.
    
    Raises:
    TypeError: If `image` is neither a string nor a Pygame Surface object.
    FileNotFoundError: If the image file cannot be loaded.
    """

    if isinstance(image, str):
        try:
            texture = pg.image.load(image)
        except pg.error as e:
            raise RuntimeError(f"Unable to load image file '{image}': {e}")
    elif isinstance(image, pg.Surface):
        texture = image
    else:
        raise TypeError("`image` should be a file path or Pygame Surface object")

    if crop:
        image_out = texture.subsurface(pg.Rect(crop[0], crop[1], crop[2], crop[3]))
    else:
        image_out = texture
        
    return pg.transform.scale_by(image_out, ratio)


# 9-Slicing Algorithm
def get_slice(width: int, height: int, texture: pg.Surface):
    w = texture.get_width()
    h = texture.get_height()
    w0 = w // 2
    h0 = h // 2
    w1 = w0 + 1
    h1 = h0 + 1
    if width < w or height < h:
        raise ValueError("Size must be at least the same as the sliced image dimensions ")
    
    gui = pg.Surface((width, height), pg.SRCALPHA)
    #gui.fill((0, 0, 0))

    # Corners
    gui.blit(texture.subsurface((0, 0, w1, h1)), (0, 0))
    gui.blit(texture.subsurface((0, h1, w0, h0)), (0, height - w0))
    gui.blit(texture.subsurface((w1, 0, w0, h0)), (width - w0, 0))
    gui.blit(texture.subsurface((w1, h1, w0, h0)), (width - w0, height - h0))

    # Sides
    gui.blit(pg.transform.scale_by(texture.subsurface((w0, 0, 1, h0)), (width - w + 1, 1)), (w0, 0))
    gui.blit(pg.transform.scale_by(texture.subsurface((w1, h0, w0, 1)), (1, height - h + 1)), (width - w0, h0))
    gui.blit(pg.transform.scale_by(texture.subsurface((w0, h1, 1, h0)), (width - w + 1, 1)), (w0, height - h0))
    gui.blit(pg.transform.scale_by(texture.subsurface((0, h0, w0, 1)), (1, height - h + 1)), (0, h0))

    # Middle
    gui.blit(pg.transform.scale_by(texture.subsurface((w0, h0, 1, 1)), (width - w + 1, height - h + 1)), (w0, h0))

    return gui.convert_alpha()