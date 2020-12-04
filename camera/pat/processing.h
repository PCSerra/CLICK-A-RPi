// Image processing classes for beacon detector
// Authors: Ondrej Cierny, Peter Grenfell
#ifndef __PROCESSING
#define __PROCESSING
#include <vector>
#include "camera.h"
#include "EasyBMP.h"

#define LINK_MAX_FRAME_HEIGHT 640

#define MAX_GROUPS 50					// Failsafe - max allowed pixel groups to process
#define MAX_ACTIVE_PIXELS 100000		// Failsafe - max allowed active pixels in frame
#define MIN_PIXELS_PER_GROUP 5			// Failsafe - minimum, in order to avoid grouping potential hot pixels

#define THRESHOLD_SAFETY_OFFSET 50		// Offset to add to histogram mean for thresholding

using namespace std;

// A group/centroid of active pixels
class Group
{
public:
	double x, y;
	unsigned int valueMax, valueSum, pixelCount;
	Group() : x(0), y(0), valueMax(0), valueSum(0), pixelCount(0) {}

	// Operator overload for sorting
	bool operator < (const Group& other) const
	{
		return valueMax > other.valueMax;
	}
};

// Base image class
class Image
{
	TCameraBinningMode binningMode;
	std::ofstream &fileStream;
	zmq::socket_t &pat_health_port;
public:
	int size;
	AOI area;
	vector<Group> groups;
	uint16_t *data, histBrightest, histPeak, histMean;
	Image(Camera &camera, std::ofstream &fileStreamIn, zmq::socket_t &pat_health_port_in, int smoothing = 0);
	~Image();
	// Processing functions
	void applyFastBlur(double radius, double passes = 2);
	uint16_t autoThresholdPeakToMax(float fraction = 1.75);
	int performPixelGrouping(uint16_t threshold = 0);
	void saveBMP(const string& filename);
};

// Log camera images
void logImage(std::string nameTag, Camera& cameraObj, std::ofstream& textFileIn, zmq::socket_t& pat_health_port, bool save_extra_exposures = false);

#endif
