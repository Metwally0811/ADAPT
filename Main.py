from flask import Flask, request, jsonify
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import subprocess
import os
import json
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

# Columns to exclude from model input
drop_cols = ['Time', 'Latitude', 'Longitude', 'Total Issues', 'Area_Problems',
             'Dominant Problem', 'Date', 'Bad Throughput', 'Spot_Area_Num',
             'Bad Coverage', 'Intra-Frequency Handover', 'Inter-Frequency Handover',
             'Overshooting', 'Overlapping', 'High Load', 'Latitude_EnodeB',
             'Longitude_EnodeB', 'Cell Identity (eNB Part)', 'Distance_Power_Check',
             'HTTP Start', 'HTTP End', 'Problem', 'overlapping_cell_ids', 'overlap_count']

# Global model placeholders
model = None
X_train = None
label_encoder = None

# ========== ROUTES ========== #

@app.route('/')
def home():
    return "<h2>Flask Backend Running</h2>"

# === Upload test file ===
@app.route('/upload-test', methods=['POST'])
def upload_test_file():
    try:
        test_file = request.files.get('file')
        if not test_file:
            return jsonify({"error": "No test file uploaded"}), 400
        # Save file in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file_path = os.path.join(current_dir, "Uploaded_Test.csv")
        test_file.save(test_file_path)
        print(f"✅ Test file saved as {test_file_path}")
        # Run the filtering script and capture output to a log file
        log_file_path = os.path.join(current_dir, "Graphs_filtering_Area_Division.log")
        with open(log_file_path, "w") as log_file:
            # Use subprocess.Popen to capture output and wait
            process = subprocess.Popen(["python", "Graphs_filtering_Area_Division.py"], stdout=log_file, stderr=log_file, cwd=current_dir)
            process.wait()
            # Check the return code for errors
            if process.returncode != 0:
                # Read the log file to include error details in the response
                with open(log_file_path, "r") as f:
                    log_content = f.read()
                # Clean up the log file after reading
                # os.remove(log_file_path) # Commenting out for now to allow manual inspection
                raise Exception(f"Graphs_filtering_Area_Division.py failed. See {log_file_path} for details.\nLog content:\n{log_content}")

        return jsonify({"message": "Test file uploaded successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Upload cell file ===
@app.route('/upload-cell', methods=['POST'])
def upload_cell_file():
    try:
        cell_file = request.files.get('file')
        if not cell_file:
            return jsonify({"error": "No cell file uploaded"}), 400
        # Save file in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cell_file_path = os.path.join(current_dir, "Uploaded_Cell.xlsx")
        cell_file.save(cell_file_path)
        print(f"📁 Cell file saved as {cell_file_path}")
        return jsonify({"message": "Cell file uploaded successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Upload RB Utilization file ===
@app.route('/upload-rb', methods=['POST'])
def upload_rb_file():
    try:
        rb_file = request.files.get('file')
        if not rb_file:
            return jsonify({"error": "No RB Utilization file uploaded"}), 400
        # Save file in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        rb_file_path = os.path.join(current_dir, "Uploaded_Utilization.xlsx")
        rb_file.save(rb_file_path)
        print(f"📊 RB Utilization file saved as {rb_file_path}")
        return jsonify({"message": "RB Utilization file uploaded successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Upload Training file ===
@app.route('/upload-train', methods=['POST'])
def upload_train_file():
    try:
        train_file = request.files.get('file')
        if not train_file:
            return jsonify({"error": "No training file uploaded"}), 400
        # Save file in the specified directory (For_ML_Results or current dir if not ML analysis)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming training files are related to ML, save it in For_ML_Results
        train_dir = os.path.join(current_dir, "For_ML_Results")
        os.makedirs(train_dir, exist_ok=True) # Ensure directory exists
        train_file_path = os.path.join(train_dir, "Uploaded_Train.csv") # Save as Uploaded_Train.csv
        train_file.save(train_file_path)
        print(f"📚 Training file saved as {train_file_path}")
        return jsonify({"message": "Training file uploaded successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Run analysis ===
@app.route('/run-analysis', methods=['POST'])
def run_analysis():
    analysis_type = request.form.get('type')  # "thresholds" or "predefined"
    print(f"🔍 Requested analysis type: {analysis_type}")

    try:
        if analysis_type == "thresholds":
            thresholds = {
                'min': float(request.form.get('min', 0)),
                'max': float(request.form.get('max', 100)),
                'throughput': float(request.form.get('throughput', 2.5)),
                'rsrp': float(request.form.get('rsrp', -110)),
                'rsrq': float(request.form.get('rsrq', -18)),
                'sinr': float(request.form.get('sinr', 3)),
                'ue': float(request.form.get('ue', 10)),
                'handover': float(request.form.get('handover', 5)),
                'distance': float(request.form.get('distance', 2)),
                'overlap': float(request.form.get('overlap', 3)),
                'prb': float(request.form.get('prb', 70)),
                'rsrp_neighbor_difference': float(request.form.get('rsrp_neighbor_difference', 6))
            }

            with open('thresholds.json', 'w') as f:
                json.dump(thresholds, f)

            # subprocess.run(["python", "Input_Filtering.py"], check=True)
            # subprocess.run(["python", "Area_Division.py"], check=True)
            # subprocess.run(["python", "Data_Analyzing.py"], check=True)
            subprocess.run(["python", "For_Code_Results/Main_Code.py"], check=True)

            subprocess.run(["python", "For_Code_Results/Dominant_Areas_Filter.py"], check=True)

            #Recommendation
            subprocess.run(["python", "For_Code_Results/Bad_Coverage_Solution/Bad_Coverage_Training_File.py"], check=True)
            subprocess.run(["python", "For_Code_Results/Bad_Coverage_Solution/BadCoverage_Recommendation.py"], check=True)
            
            subprocess.run(["python", "For_Code_Results/Highload_Solution/Highload_Recommendation.py"], check=True)

            subprocess.run(["python", "For_Code_Results/Overlapping_Solution/Overlapping_Training_File.py"], check=True)
            subprocess.run(["python", "For_Code_Results/Overlapping_Solution/Overlapping_Recommendation.py"], check=True)

            output_file = os.path.join("For_Code_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            output_file_abs = os.path.abspath(output_file)
            if os.path.exists(output_file_abs):
                return jsonify({"message": "Threshold-based analysis complete", "output_file": output_file_abs})
            return jsonify({"error": "Threshold output file not found"}), 500

        # elif analysis_type == "predefined":
        #     if 'file' in request.files:
        #         train_file = request.files['file']
        #         train_file.save("Uploaded_Train.csv")
        #         # train_path = "Uploaded_Train.csv"
        #         print("📁 Using uploaded training file.")
        #     else:
        #         train_file.save("Train_old.csv")
        #         # train_path = "Train_old.csv"
        #         print("📄 Using default Train_old.csv.")

        #     # train_df = pd.read_csv(train_path)
        #     # X = train_df.drop(columns=[col for col in drop_cols if col in train_df.columns], errors='ignore')
        #     # label_encoder = LabelEncoder()
        #     # y = label_encoder.fit_transform(train_df['Dominant Problem'].astype(str))

        #     # clf = RandomForestClassifier(random_state=3)
        #     # clf.fit(X, y)

        #     # test_file_path = "Uploaded_Test.csv"
        #     # if not os.path.exists(test_file_path):
        #     #     return jsonify({"error": "Test file not uploaded yet."}), 400

        #     # test_df = pd.read_csv(test_file_path)
        #     # test_X = test_df[X.columns]

        #     # pred_encoded = clf.predict(test_X)
        #     # pred_labels = label_encoder.inverse_transform(pred_encoded)

        #     # test_df["Predicted Dominant Problem"] = pred_labels
        #     # output_file = "new_predictions.xlsx"
        #     # test_df.to_excel(output_file, index=False)
            
        #     #AAAAAAAAA
        #     subprocess.run(["python", "For_ML_Results/Reg_problem_identification.py"], check=True)

        #     subprocess.run(["python", "For_ML_Results/Dominant_Areas_Filter.py"], check=True)
        #     subprocess.run(["python", "For_ML_Results/Bad_Coverage_Solution/Bad_Coverage_Training_File.py"], check=True)
        #     subprocess.run(["python", "For_ML_Results/Bad_Coverage_Solution/BadCoverage_Recommendation.py"], check=True)
        

        #     return jsonify({"message": "Predefined ML prediction complete", "output_file": output_file})
        elif analysis_type == "predefined":
            # Determine training file name
            if 'file' in request.files and request.files['file'].filename != '':
                train_file = request.files['file']
                train_file.save("For_ML_Results/Uploaded_Train.csv")
                print("📁 Uploaded training file saved as Uploaded_Train.csv")
            else:
                # Copy fallback file if user didn't upload one
                if not os.path.exists("Nasr_City_Training_File.csv"):
                    return jsonify({"error": "Default training file 'Nasr_City_Training_File.csv' not found."}), 500
                # Ensure fallback file is copied/renamed for downstream script
                import shutil
                shutil.copy("Nasr_City_Training_File.csv", "For_ML_Results/Uploaded_Train.csv")
                print("📄 Using fallback training file (Nasr_City_Training_File.csv) as Uploaded_Train.csv")


            print("📄 Using fallback training file (Nasr_City_Training_File.csv) as Uploaded_Train.csv")
            # Run ML processing pipeline
            subprocess.run(["python", "For_ML_Results/Reg_problem_identification.py"], check=True)
            subprocess.run(["python", "For_ML_Results/Dominant_Areas_Filter.py"], check=True)

            #Recommendation
            subprocess.run(["python", "For_ML_Results/Bad_Coverage_Solution/Bad_Coverage_Training_File.py"], check=True)
            subprocess.run(["python", "For_ML_Results/Bad_Coverage_Solution/BadCoverage_Recommendation.py"], check=True)

            subprocess.run(["python", "For_ML_Results/Highload_Solution/Highload_Recommendation.py"], check=True)
          
            subprocess.run(["python", "For_ML_Results/Overlapping_Solution/Overlapping_Training_File.py"], check=True)
            subprocess.run(["python", "For_ML_Results/Overlapping_Solution/Overlapping_Recommendation.py"], check=True)

            # Determine if default file was used based on the presence of 'file' in the request
            used_default = 'file' not in request.files or request.files['file'].filename == ''

            response_data = {"message": "Predefined ML analysis complete", "output_file": "Problem_Areas_ML_Output.csv"}
            if used_default:
                response_data['used_default_train_file'] = True

            return jsonify(response_data)

        else:
            return jsonify({"error": "Invalid analysis type provided."}), 400

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Script error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

""" # === Standalone prediction endpoint ===
@app.route('/predict', methods=['POST'])
def predict():
    if model is None or X_train is None or label_encoder is None:
        return jsonify({"error": "Model not initialized."}), 500

    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No CSV file uploaded"}), 400

        test_df = pd.read_csv(file)
        test_X = test_df[X_train.columns]

        predictions_encoded = model.predict(test_X)
        predictions_decoded = label_encoder.inverse_transform(predictions_encoded)

        test_df["Predicted Dominant Problem"] = predictions_decoded
        output_file = "new_predictions.xlsx"
        test_df.to_excel(output_file, index=False)

        return jsonify({"message": "Prediction complete", "output_file": output_file})

    except Exception as e:
        return jsonify({"error": str(e)}), 500 """

# ========== START BACKEND ========== #
if __name__ == '__main__':
    app.run(port=3000, debug=True)
