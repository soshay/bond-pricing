import sys
import numpy as np
import scipy as sc
from scipy.special import gamma

def q_alpha(p=None, y=None, r=None,q=None, alpha=None, sigma=None, t=None):

	'''The Q-Alpha Bond Default Model

	This method implements the q-alpha bond survival model, as
	described by Stanford Prof. Lisa Borland here:
	<https://arxiv.org/pdf/cond-mat/0501395.pdf>. Adapted
	from code provided in Northwestern's MS&E 444 course.
	
	This method runs a 1000 path Monte-Carlo simulation to 
	generate the output value.

	Inputs:
	
	p = the current price of the bond
	y = the current yield of the bond
	r = the estimated recovery rate in case of default
	q = the kurtosis of the Tsallis distribution
	alpha = the skewness of the Tsallis distribution
	sigma = annualized variance of bond
	t = time horizon (must be whole years)

	Output:
	
	prob_of_default = the probability of default within the 
	specified time horizon

	Sample Inputs

	p = 80 (pennies on the dollar)
	y = 0.10 (decimal, 10%)
	r = 0.65 (decimal, 65%)
	q = 1.3
	alpha = 2
	sigma = 0.55 
	t = 3 (years)
	'''

	# INITIALIZATION

	# Number of Monte-Carlo paths
	npaths = 1000
	
	# If prices falls below expected recovery, assume default
	r = r * p
	days = 365 * t
	# Variable dt is the timestep
	dt = t / days
	# Must save to calculate survival rate
	npaths_initial = npaths
	# Prices by day
	pre_prices = np.zeros((days, npaths))
	# Fluctuating prices
	post_prices = np.zeros(npaths) + p
	
	# MAIN LOOP 
	
	# Omega is daily change by path
	omega = np.zeros(npaths)
	num_defaults = 0
	t = np.arange(dt, t + 1, dt)
	for iter in range(0, days):
		# Tsallis Q-Alpha prices update
		updated_price = closed_form_price(omega, t[iter], q)
		sigma_factor = sigma * (t[iter] ** ((1 - q) / (2*(3 - q))))
		adj_random_matrix = np.random.randn(npaths, 1) * (dt ** 0.5)
		adj_random_matrix = adj_random_matrix.reshape((npaths,))
		# Add value of period yield
		post_prices += y * dt * post_prices
		# Add volatility in price change
		vol_lhs = sigma_factor * (p ** (1 - alpha)) * (post_prices ** alpha)
		vol_rhs = np.multiply(updated_price ** ((1 - q) / 2), adj_random_matrix)
		post_prices += np.multiply(vol_lhs, vol_rhs) 
		pre_prices[iter, :] = post_prices.T
		omega += (updated_price ** ((1 - q) / 2)) * adj_random_matrix
	
		# Check for defaulted bond states
		is_defaulted = np.nonzero(pre_prices[iter,] < r)
		if len(is_defaulted[0]) > 0:
			# Remove defaulted paths
			omega = np.delete(omega, is_defaulted[0])
			pre_prices = np.delete(pre_prices, is_defaulted[0], 1)
			npaths = npaths - len(is_defaulted[0])
			num_defaults += len(is_defaulted[0])

		# Iterate with transpose
		post_prices = pre_prices[iter, :].T

	# Calculate percentage of defaulted lines
	prob_of_default = num_defaults / npaths_initial
	return prob_of_default
	
def closed_form_price(omega=None, t=None, q=None):

	'''Closed form bond pricing update solution.
	
	Adapted from code provided in Northwestern's MS&E 444 course.
	'''

	gamma_top = gamma((1 / (q - 1) - 0.5))
	gamma_bottom = gamma(1 / (q - 1))
	gamma_frac = (gamma_top / gamma_bottom) ** 2
	adjusted_q = (sc.pi / (q - 1)) * gamma_frac
 
	rhs = (t * (2 - q) * (3 - q)) ** (-2 / (3 - q))
	beta_value = adjusted_q ** ((1 - q) / (3 - q)) * rhs
	
	zeta_value = (t * adjusted_q * (2 - q) * (3 - q)) ** (1 / (3 - q))
	rhs = (1 + (omega ** 2.0) * beta_value * (q - 1)) ** (- 1 / (q - 1))
	new_price = (1.0 / zeta_value) * rhs
	return new_price

def sensitivity(data=None, q=None, alpha=None, sigma=None, t=None):

	'''Sensitivity analysis on recovery rate

	This method performs a sensitivity analysis on the 
	q-alpha probability of bond default given differing
	recovery rates. In particular, this method takes in
	a two-column data matrix, in which the first column is 
	the price of a bond (in pennies on the dollar) and the
	second column is the yield in basis points (as is the case
	on the Bloomberg TACT screen. See the accompanying 
	q_alpha method for information on the remaining inputs.
	
	For each row (bond) in the input prices_and_yields, the method
	uses the specified hyper paramters to evaluate the probability
	of default given each recovery rate in 5% increments from 10%
	to 90%.
	'''

	# Recovery rate range	
	rates = np.arange(0.1, 0.9, 0.05)
	
	# Result matrix is bond by recovery rate in range above
	rate_sens = np.zeros((data.shape[0], rates.shape[0]))
	message_right = " of " + str(data.shape[0] * rates.shape[0]) + " complete."
	num_completed = 1
	for r in range(0, rates.shape[0]):
		for i in range(0, data.shape[0]):
			p = data[i, 0]
			# Adjust yield from Bloomberg format to bps
			y =  data[i, 1] / 100
			rate_sens[i, r] = q_alpha(p, y, rates[r], q, alpha, sigma, t)
			# Print an update
			print("Outcome " + str(num_completed) + message_right)
			num_completed += 1
	return rate_sens

def main():
	
	'''Main Method

	This script takes in five additional arguments from the command
	line. The first argument must be the name of a .csv file 
	in the current directory. It should contain the bond prices
	and yields under consideration. The first row of the file
	must be a header, and the prices should be in pennies on the
	dollar, while the yields should be in basis points. This is
	the same representation as the Bloomberg TACT screen.

	The second, third, fourth, and fifth arguments should be the 
	q, alpha, sigma, and t values for the q-alpha model above.

	See the q_alpha() function for more variable explanation.

	This script then runs a sensitivity analysis on the q_alpha
	probability of default for recovery rates between 10% and 90%.

	It then outputs the results to a headerless .csv file. 
	
	From command line, a call may be made:
	
	>> python3 bond_default_analysis.py [bond_data.csv] [q] [alpha] [sigma] [t]
	'''
	
	if len(sys.argv) < 6:
		print("Please enter data file name, model parameters.")
	else:
		# Extract inputs
		data = np.loadtxt(sys.argv[1], delimiter=",", skiprows=1)
		q = float(sys.argv[2])
		if q <= 1:
			print("Q must be greater than 1.")
			exit()
		alpha = float(sys.argv[3])
		sigma = float(sys.argv[4])
		t = int(sys.argv[5])
		# Run analysis
		rate_sens = sensitivity(data, q, alpha, sigma, t)
		# Save to file
		np.savetxt("default_sensitivity.csv", rate_sens, delimiter=",", fmt='%1.4f')
		print("Success! See default_sensitivity.csv.")
	
if __name__ == "__main__": main()

