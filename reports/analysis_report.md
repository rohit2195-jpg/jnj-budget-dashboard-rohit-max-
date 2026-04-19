# Housing Market Analysis

## Executive Summary
This report analyzes a dataset of **4140 count** total housing listings. The average house price across all listings is **$553,062.86 USD**, with a median price of $460,000.00 USD, indicating a market skewed towards higher-value properties. Key factors influencing price include location, waterfront access, and property condition. Analysis of sales volume shows significant monthly fluctuations, with June 2014 being the peak sales period.

### Total Housing Listings
The dataset contains a total of **4140 count** property listings. This volume provides a comprehensive basis for analyzing the market's characteristics.

### Average House Price
The average price for a house in this dataset is **$553,062.86 USD**. This figure serves as a general benchmark for the market, though it is influenced by a wide range of property values.

### Median House Price
The median house price is **$460,000.00 USD**. This value represents the midpoint of the market and is less susceptible to outliers than the average, suggesting that more than half of the properties are listed below the average price.

### Average Living Area
The average property features a living area of **2143.64 sqft**. This provides a sense of the typical property size available in this market.

### Average Housing Price by City
Medina has the highest average housing price at **$2,046,559.09 USD**, followed by Clyde Hill at $1,343,140.00 USD and Yarrow Point at $1,194,837.50 USD. Excluding the "Other" category, Seattle has the lowest average price among the top 14 cities at $577,681.22 USD.

### Number of Listings by City
Seattle has the most listings with a total of **1415.0 count**, significantly more than any other city. Renton and Bellevue follow with 261.0 count and 260.0 count, respectively. Among the top 14 cities, Mercer Island has the fewest listings at 81.0 count.

### Average Price: Waterfront vs. Non-Waterfront
Properties with a waterfront view have an average price of **$1,435,967.74 USD**, which is more than double the $546,401.86 USD average for non-waterfront properties.

### Monthly Sales Volume
Sales volume peaked in 2014-06 with **2179 count** houses sold. The lowest volume was observed in 2014-07 with 653 count sales, a sharp decrease from the prior month.

### Monthly Average House Price
The monthly average house price reached its highest point in 2014-07 at **$614,407.80 USD**. The lowest point in the observed period was in 2014-05, with an average price of $530,924.56 USD.

### Price vs. Living Area (sqft)
Based on a sample of 500 properties, there is a clear positive relationship between living area and price. The most expensive property in the sample is priced at **$3,000,000.00 USD** with a living area of 4850.0 sqft. Several properties in the sample were listed with a price of $0.00 USD, likely indicating data entry errors.

### Price vs. Year Built
The relationship between price and the year built is not linear. Newer homes do not always command higher prices. For instance, a home built in 1934 is priced at $2,027,000.00 USD, while a home built in 2014 is priced at **$224,000.00 USD**, based on a sample of 500 properties.

### Price by Condition and Renovation Status
For homes in the highest condition rating (Condition 5), renovated properties have an average price of **$699,078.82 USD**. This is notably higher than the $612,335.09 USD average for non-renovated homes in the same condition category. Interestingly, for homes in Condition 4, non-renovated properties have a slightly higher average price ($551,338.85 USD) than renovated ones ($513,037.94 USD).

## Additional Insights
- **Geographic Disparity:** The market is heavily concentrated in Seattle, which has more than five times the listings of the next closest city, Renton. However, the highest average prices are found in smaller, more exclusive cities like Medina, where the average price exceeds **$2,000,000.00 USD**.
- **Waterfront Premium:** Waterfront access is the single most significant price driver identified, adding an average of nearly **$900,000.00 USD** to a property's value compared to non-waterfront homes.
- **Market Volatility:** The sharp drop in sales volume from 2179 count in June 2014 to 653 count in July 2014, coupled with a simultaneous rise in average price, suggests a potential shift in market dynamics or inventory during that period.

## Forecast
Based on linear regression (R² = 0.90), the monthly average house price is trending **upward**. The model projects that prices will continue to grow by approximately $41,742.00 USD per month. By the second projected period (2014-07+2), the average price is forecast to reach **$689,658.37 USD**, with a 95% confidence interval of $594,196.31 – $785,120.43 USD.