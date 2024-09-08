from flask import Flask, request, jsonify, current_app, send_file
import os
import shutil
from db import get_db

app = Flask(__name__)

# ZFS pool name
STATIC_ZPOOL_NAME = "s3" 

@app.route('/delete_bucket/<bucket>', methods=['DELETE'])
def delete_bucket(bucket):
    try:
        path = f'/{STATIC_ZPOOL_NAME}/{bucket}'
        if os.path.exists(path):
            shutil.rmtree(path)  
            current_app.logger.info(f"Bucket '{bucket}' deleted successfully from path '{path}'.")
        else:
            current_app.logger.warning(f"Bucket '{bucket}' not found at path '{path}'.")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM objects WHERE bucket=%s", (bucket,))
        db.commit()
        cursor.close()

        current_app.logger.info(f"All records associated with bucket '{bucket}' deleted from the database")
        return jsonify({"message": f"Bucket '{bucket}' and all associated records deleted successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting bucket '{bucket}': {e}")
        return jsonify({"error": "Failed to delete bucket"}), 500

@app.route('/upload/<bucket>/<path:key>', methods=['PUT'])
def upload_file(bucket, key):
    try:
        key = key.rstrip('/')

        zpool_name = STATIC_ZPOOL_NAME
        base_path = f'/{zpool_name}/{bucket}'
        os.makedirs(base_path, exist_ok=True)

        # If the key contains subdirectories, create them too
        key_parts = key.split('/')
        if len(key_parts) > 1:
            prefix = '/'.join(key_parts[:-1])
            directory_path = f'{base_path}/{prefix}'
            os.makedirs(directory_path, exist_ok=True)

        path = f'{base_path}/{key}'

        file = request.files['file']
        file.save(path)
        current_app.logger.info(f"File '{key}' uploaded to '{path}'.")

        db = get_db()
        cursor = db.cursor()

        file_size = os.path.getsize(path)
        node_name = get_node_id()
        cursor.execute(
            "SELECT id FROM objects WHERE bucket=%s AND key=%s",
            (bucket, key)
        )
        existing_record = cursor.fetchone()

        if existing_record:
            cursor.execute(
                "UPDATE objects SET node_name = %s, path = %s, size = %s, created_at = current_timestamp WHERE id = %s",
                (node_name, path, file_size, existing_record[0])
            )
            current_app.logger.info(f"File metadata for '{key}' updated in database")
        else:
            cursor.execute(
                "INSERT INTO objects (bucket, key, node_name, path, size) VALUES (%s, %s, %s, %s, %s)",
                (bucket, key, node_name, path, file_size)
            )
            current_app.logger.info(f"New file metadata for '{key}' inserted into database")

        db.commit()
        cursor.close()

        return jsonify({"message": "File uploaded and metadata stored successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error uploading file '{key}' to bucket '{bucket}': {e}")
        return jsonify({"error": "Failed to upload file"}), 500
    
@app.route('/<bucket>/<path:key>', methods=['DELETE'])
def delete_file(bucket, key):
    try:
        key = key.rstrip('/')
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT node_name, path FROM objects WHERE bucket=%s AND key=%s",
            (bucket, key)
        )
        existing_record = cursor.fetchone()

        if not existing_record:
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found for deletion")
            return jsonify({"error": "File not found"}), 404

        node_name, path = existing_record

        if os.path.exists(path):
            os.remove(path)
            cursor.execute(
                "DELETE FROM objects WHERE bucket=%s AND key=%s",
                (bucket, key)
            )
            db.commit()
            cursor.close()
            current_app.logger.info(f"File '{key}' in bucket '{bucket}' deleted from node '{node_name}'.")
            return jsonify({"message": "File deleted successfully"}), 200
        else:
            cursor.close()
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found on disk for deletion")
            return jsonify({"error": "File not found on disk"}), 404

    except Exception as e:
        current_app.logger.error(f"Error deleting file '{key}' from bucket '{bucket}': {e}")
        return jsonify({"error": "Failed to delete file"}), 500

@app.route('/<bucket>/<path:key>', methods=['HEAD'])
def head_file(bucket, key):
    try:
        key = key.rstrip('/')
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT node_name, path, size FROM objects WHERE bucket=%s AND key=%s",
            (bucket, key)
        )
        existing_record = cursor.fetchone()

        if not existing_record:
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found.")
            return jsonify({"error": "File not found"}), 404

        node_name, path, size = existing_record

        if os.path.exists(path):
            current_app.logger.info(f"File '{key}' in bucket '{bucket}' found on node '{node_name}'.")
            return jsonify({"message": "File exists", "size": size}), 200
        else:
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found on disk")
            return jsonify({"error": "File not found on disk"}), 404

    except Exception as e:
        current_app.logger.error(f"Error checking file '{key}' in bucket '{bucket}': {e}")
        return jsonify({"error": "Failed to check file"}), 500

@app.route('/<bucket>/<path:key>', methods=['GET'])
def get_file(bucket, key):
    try:
        key = key.rstrip('/')
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT node_name, path FROM objects WHERE bucket=%s AND key=%s",
            (bucket, key)
        )
        existing_record = cursor.fetchone()

        if not existing_record:
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found")
            return jsonify({"error": "File not found"}), 404

        node_name, path = existing_record

        if os.path.exists(path):
            current_app.logger.info(f"Serving file '{key}' from bucket '{bucket}' on node '{node_name}'.")
            return send_file(path)
        else:
            current_app.logger.warning(f"File '{key}' in bucket '{bucket}' not found on disk")
            return jsonify({"error": "File not found on disk"}), 404

    except Exception as e:
        current_app.logger.error(f"Error retrieving file '{key}' from bucket '{bucket}': {e}")
        return jsonify({"error": "Failed to retrieve file"}), 500

def get_node_id():
    try:
        with open('/tmp/node-id', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)