import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("📊 Simple Streamlit App")

st.write("Upload a CSV file to see your data and a basic chart!")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("Preview of the data")
    st.dataframe(df.head())

    # Select a column to plot
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if numeric_cols:
        column = st.selectbox("Select a column to visualize", numeric_cols)
        fig, ax = plt.subplots()
        df[column].hist(ax=ax, bins=20)
        st.pyplot(fig)
    else:
        st.warning("No numeric columns found in the data.")
else:
    st.info("Please upload a CSV file to get started.")
