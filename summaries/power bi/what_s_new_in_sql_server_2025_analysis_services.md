What’s New in SQL Server 2025 Analysis Services (, 2025-07-15)
Source: https://powerbi.microsoft.com/en-us/blog/whats-new-in-sql-server-2025-analysis-services
Summary: The preview of SQL Server 2025 is now available at aka.ms/getsqlserver2025! This preview includes many exciting enhancements for SQL Server Analysis Services (SSAS).

 SQL Server 2025 Analysis Services (SSAS) introduces a range of enhancements across performance, modeling, diagnostics, and DAX capabilities.
Key Features:
• .ms/getsqlserver2025! This preview includes many exciting enhancements for SQL Server Analysis Services (SSAS)
• . SQL Server 2025 Analysis Services (SSAS) introduces a range of enhancements across performance, modeling, diagnostics, and DAX capabilities
• . INFO Functions: The existing TMSCHEMA DMVs are now available as a new family of DAX functions, which allows querying metadata about semantic models directly within DAX, offering integration with other DAX functions for enhanced diagnostics and analysis
• .: The existing TMSCHEMA DMVs are now available as a new family of DAX functions, which allows querying metadata about semantic models directly within DAX, offering integration with other DAX functions for enhanced diagnostics and analysis
• . Unicode Character Handling Enhancements SSAS now supports updated Unicode standards by providing Unicode surrogate pair support for character standards such as the Chinese government standard GB18030 in DAX
• . Content: Performance Improvements DAX Functions and Capabilities Additional Features Deprecated Features and Breaking Changes Next Steps Performance Improvements Models with calculation groups and format strings in Excel We have made significant performance improvements for MDX queries on models with Calculation Groups and Format Strings to reduce memory usage and improve responsiveness! The latest changes will greatly improve the performance and reliability of operations in Analyze in Excel on models that include one or both of: Dynamic Format Strings for Measures Calculated Items with Format Strings For more details, refer to the Dynamic format strings documentation
• . Parallel Query Execution for DirectQuery Improved parallelism in DirectQuery mode enables faster response times for complex queries
• . DAX Functions Improvements SSAS 2025 includes support for multiple new DAX functions and improvements including: LINEST and LINESTX : These two functions perform linear regression, leveraging the Least Squares method, to calculate a straight line that best fits the given data and return a table describing that line
• . Additional Features Client Library Updates Customers are encouraged to upgrade to the latest Analysis Services libraries to benefit from performance, reliability and functionality improvements such as binary XML support, TMDL serialization, and more
Executive Insight: This announcement highlights new capabilities or strategic direction relevant to customers or the business.
