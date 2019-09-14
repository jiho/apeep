# I/O settings
input_dir = '/media/visufront/11B/lagrangian-15' # NB: should not have trailing slash
output_dir = '../apeep_unstacked/lagrangian-15'

# Wether to print debug messages
debug = False

# Characteristics of the original images
# orientation of the top of the picture
# valid values are 'right' and 'left'
top = 'right'
# number of lines scanned per second
scan_per_s = 28000

# Moving average window size (in px) for flat-fielding
# larger values avoid white streaks after dark objects but are longer to compute and less reactive
# probably needs to be > 2000
window_size = 8000   # in px

# Output settings
# size of the output frame (in nb of original frames)
# this is the size of the image which gets processed and possibly written on disk
# larger values avoid clipping objects between frames and are probably more CPU efficient (but more memory consuming)
output_size = 10
# whether to write the flat-fielded output image on disk
write_ff_image = False
# whether to write the processed output image on disk (lightened after flat fielding)
write_processed_image = False

# Output image processing
# percentage of light grey pixels to clip to white
# in [0,100]; 0 changes nothing, 100 makes everything white
# most of the image is almost white so values around 75 are common
light_threshold = 85
# Threshold
# for dynamic threshold : percentage of dark grey pixels to clip to black and consider as particles
# for static threshold  : grey value below which dark grey pixels are clipped to black and considered as particles
# in [0, 100]; 0 considers nothing, 100 considers all pixels
dark_threshold = 1.3
# method to determine the threshold level for dark pixels to be considered as particles
# valid values are 'dynamic', 'static'
dark_threshold_method = 'dynamic'

# Particles processing
# whether to detect particles
detect_particles = True
# whether to write the output image with a read mask over detected particles
write_mask_image = False
# number of pixel to grow thresholded particles by (in px)
# sane values are 0 to 15
dilate = 5
# minimum area of particles to me measured and written out (in px)
# sane values are ~50 to a few hundred
min_area = 500
# padding around the particle in the output image (in px)
# sane values are 0 to ~10
pad = 4
# properties of particles to store in the particles.csv file
# see http://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops
properties_labels = ['label',
                     'area',
                     'orientation',
                     'centroid',
		     'bbox']
# properties_labels = ['label',
#                      'area',
#                      'convex_area',
#                      'filled_area',
#                      'eccentricity',
#                      'equivalent_diameter',
#                      'euler_number',
#                      'inertia_tensor_eigvals',
#                      'major_axis_length',
#                      'minor_axis_length',
#                      'max_intensity',
#                      'mean_intensity',
#                      'min_intensity',
#                      'moments_hu',
#                      'weighted_moments_hu',
#                      'perimeter',
#                      'orientation',
#                      'centroid']
# TODO move that into an options file which gets imported
