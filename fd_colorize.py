#!/usr/bin/python

import cv2
import os,sys,copy
import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression

PatchSize = 27
PatchStride = PatchSize*10

def PatchExtractor(image,psize,stride=None):
	assert(psize%2 == 1) # Patch size must be odd

	patches = []
	# ytrain = np.zeros( (image.shape[0] - (1+psize),image.shape[1] - (1+psize)) )
	utrain = np.zeros(( (1+image.shape[0]-psize)//stride, (1+image.shape[1]-psize)//stride ))
	vtrain = np.zeros(( (1+image.shape[0]-psize)//stride, (1+image.shape[1]-psize)//stride ))
	if stride is None:
		stride = psize

	dim = 0 # Use only Y (Luminance)
	
	# for dim in range(image.shape[2]):
	for ny in range( (1+image.shape[1]-psize)//stride ):
		for nx in range( (1+image.shape[0]-psize)//stride ):
			# patches.append(image[nx*stride:(nx*stride)+psize,ny*stride:(ny*stride)+psize,dim])
			patch = image[nx*stride:(nx*stride)+psize,ny*stride:(ny*stride)+psize,dim]
			# print patch.reshape((-1,1)).shape
			patches.append( patch.reshape((1,-1)))
			utrain[nx,ny] = image[(nx*stride)+(psize//2),(ny*stride)+(psize//2),1]
			vtrain[nx,ny] = image[(nx*stride)+(psize//2),(ny*stride)+(psize//2),2]

	# UV Values to train for regression
	utrain = utrain.reshape((-1,1))
	vtrain = vtrain.reshape((-1,1))
	return np.vstack(patches),utrain,vtrain

def AssignColor(image,kmodel,u_reg_models,v_reg_models,psize): #Image should be YUV
	p_by2 = psize//2
	patches = []
	patch_centers = []
	for px in range( p_by2, image.shape[0]-p_by2 ):
		for py in range( p_by2, image.shape[1]-p_by2 ):
			patch = image[ px-p_by2:1+px+p_by2, py-p_by2:1+py+p_by2, 0]
			patches.append( patch.reshape((1,-1)) )
			patch_centers.append( [px,py] )
	
	patches = np.vstack(patches)
	# print patches.shape
	mean_labels = kmodel.predict( patches )
	# u_val = u_reg_models[mean_label].predict()

	for i,pt in enumerate(kmodel.cluster_centers_):
		indices = [mean_labels == i]
		# print "Len of patch_centers:",len(patch_centers)
		# print "Shape of indices:",indices.shape
		# print indices
		for ind in range(len(patch_centers)):
			if indices[0][ind] is False:
				# print 'False'
				continue
			# print "ind:",ind
			# print "patch_centers:", patch_centers[ind]
			# px,py = patch_centers[ind][0], patch_centers[ind][1]
			# u_patch = image[ px-p_by2:1+px+p_by2, py-p_by2:1+py+p_by2, 0]
			# v_patch = image[ px-p_by2:1+px+p_by2, py-p_by2:1+py+p_by2, 0]
			u_val = u_reg_models[i].predict( patches[ind].reshape(1,-1) )
			v_val = v_reg_models[i].predict( patches[ind].reshape(1,-1) )
			
			if ind%1000 == 0:
				string = "\rProgress: %5.2f " % ( 100.0*ind/len(patch_centers) )
				sys.stdout.write(string)
				sys.stdout.flush()
		print "Phase completed: ", i+1," out of ",len(kmodel.cluster_centers_)

	pass

# while cv2.waitKey(0) != 27:
# 	pass

if __name__ == "__main__":
	S = cv2.imread("img_color.jpg") # Source color image
	T = cv2.imread("img_gray.jpg",0) # Target gray image

	# YUV Conversion
	S = cv2.cvtColor(cv2.imread("img_color.jpg"),cv2.COLOR_BGR2YUV) 
	T = cv2.cvtColor(cv2.imread("img_gray.jpg",0),cv2.COLOR_GRAY2BGR) 
	T = cv2.cvtColor(T,cv2.COLOR_BGR2YUV)

	patches,u_vals,v_vals = PatchExtractor(S,PatchSize,PatchStride)
	print "Patches shape:",patches.shape

	lrmodel = LinearRegression(n_jobs=-1)
	kmodel = KMeans(n_clusters=3,n_jobs=-1)
	labels = kmodel.fit_predict(patches)
	print "KMeans Model fit done!"

	mean_patch = np.zeros((PatchSize,PatchSize))
	u_reg_models = []
	v_reg_models = []

	for i,pt in enumerate(kmodel.cluster_centers_):
		mean_patch = pt.reshape(PatchSize,PatchSize)
		mean_patch = np.uint8(mean_patch)
		mean_patch = cv2.cvtColor(mean_patch,cv2.COLOR_GRAY2BGR)
		# print mean_patch
		# cv2.imshow("Mean patch",mean_patch)
		# cv2.waitKey(0)
		nearest_points = patches[labels == i,]
		u_regress = u_vals[labels == i]
		v_regress = v_vals[labels == i]

		# To verify that average of the spliced points is actually the mean_patch, use this line:
		# print "Average: ",np.average(nearest_points,axis=0),"\nvs mean:",pt

		print "nearest_points:",nearest_points.shape
		lrmodel.fit(nearest_points,u_regress)
		u_reg_models.append( copy.deepcopy(lrmodel) )
		lrmodel.fit(nearest_points,v_regress)
		v_reg_models.append( copy.deepcopy(lrmodel) )

	AssignColor(T,kmodel,u_reg_models,v_reg_models,PatchSize)

