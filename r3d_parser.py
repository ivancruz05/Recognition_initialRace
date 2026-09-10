"""
Parser de archivos .r3d de Record3D.
Extrae frames RGB y depth maps del LiDAR.

Uso:
    from r3d_parser import R3DParser
    
    parser = R3DParser("video.r3d")
    frames, depths = parser.extract_all()
    parser.save_frames("output/")
"""

import json
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple, List, Optional

import cv2
import numpy as np

# Verificar si lzfse está disponible
def _check_lzfse():
    """Verifica si lzfse está instalado."""
    try:
        result = subprocess.run(['lzfse', '-h'], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

HAS_LZFSE = _check_lzfse()
if not HAS_LZFSE:
    print("[Warning] lzfse no instalado. Los depth maps no se pueden descomprimir.")
    print("  Instalar con: brew install lzfse")


class R3DParser:
    """Parser para archivos .r3d de Record3D."""
    
    def __init__(self, r3d_path: str):
        """
        Args:
            r3d_path: ruta al archivo .r3d
        """
        self.path = Path(r3d_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {r3d_path}")
        
        self._metadata = None
        self._frames = None
        self._depths = None
    
    @property
    def metadata(self) -> dict:
        """Metadata del archivo .r3d."""
        if self._metadata is None:
            self._load_metadata()
        return self._metadata
    
    def _load_metadata(self):
        """Carga metadata del archivo .r3d."""
        with zipfile.ZipFile(self.path, 'r') as z:
            if 'metadata' in z.namelist():
                with z.open('metadata') as f:
                    self._metadata = json.load(f)
            elif 'metadata.json' in z.namelist():
                with z.open('metadata.json') as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {}
    
    def _get_frame_files(self) -> Tuple[List[str], List[str], List[str]]:
        """Obtiene listas de archivos RGB, depth y confidence."""
        with zipfile.ZipFile(self.path, 'r') as z:
            all_files = z.namelist()
            
            # Formato Record3D: rgbd/XXX.jpg y rgbd/XXX.depth
            rgb_files = sorted([f for f in all_files if f.startswith('rgbd/') and f.endswith('.jpg')])
            depth_files = sorted([f for f in all_files if f.startswith('rgbd/') and f.endswith('.depth')])
            conf_files = sorted([f for f in all_files if f.startswith('rgbd/') and f.endswith('.conf')])
            
            return rgb_files, depth_files, conf_files
    
    def get_info(self) -> dict:
        """Retorna información básica del archivo."""
        meta = self.metadata
        rgb_files, depth_files, conf_files = self._get_frame_files()
        
        # Obtener dimensiones de la imagen
        img_w = meta.get('w', 1440)
        img_h = meta.get('h', 1920)
        
        return {
            'file': str(self.path),
            'size_mb': self.path.stat().st_size / (1024 * 1024),
            'rgb_frames': len(rgb_files),
            'depth_frames': len(depth_files),
            'conf_frames': len(conf_files),
            'has_lzfse': HAS_LZFSE,
            'width': img_w,
            'height': img_h,
        }
    
    def _lzfse_decompress(self, data: bytes) -> Optional[bytes]:
        """Descomprime datos LZFSE usando el comando lzfse."""
        if not HAS_LZFSE:
            return None
        
        try:
            # Crear archivos temporales
            with tempfile.NamedTemporaryFile(suffix='.lzfse', delete=False) as tmp_in:
                tmp_in.write(data)
                tmp_in_path = tmp_in.name
            
            tmp_out_path = tmp_in_path + '.out'
            
            # Ejecutar lzfse
            result = subprocess.run(
                ['lzfse', '-decode', '-i', tmp_in_path, '-o', tmp_out_path],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Intentar sin -decode
                result = subprocess.run(
                    ['lzfse', '-i', tmp_in_path, '-o', tmp_out_path],
                    capture_output=True,
                    timeout=10
                )
            
            # Leer resultado
            if Path(tmp_out_path).exists():
                with open(tmp_out_path, 'rb') as f:
                    decompressed = f.read()
                
                # Limpiar
                Path(tmp_in_path).unlink()
                Path(tmp_out_path).unlink()
                
                return decompressed
            else:
                Path(tmp_in_path).unlink()
                return None
                
        except Exception as e:
            print(f"  [Error] LZFSE: {e}")
            return None
    
    def _read_depth_file(self, z: zipfile.ZipFile, depth_path: str) -> Optional[np.ndarray]:
        """Lee un archivo .depth y lo convierte a numpy array.
        
        Record3D guarda depth como float32 comprimido con LZFSE.
        LiDAR: 256x192 px, FaceID: 640x480 px.
        """
        try:
            with z.open(depth_path) as f:
                data = f.read()
            
            if not HAS_LZFSE:
                print(f"  [Warning] lzfse no disponible, no se puede descomprimir {depth_path}")
                return None
            
            # Descomprimir con LZFSE
            decompressed = self._lzfse_decompress(data)
            
            if decompressed is None:
                return None
            
            # Convertir a float32 (cada 4 bytes = 1 pixel de profundidad en metros)
            depth = np.frombuffer(decompressed, dtype=np.float32)
            
            # Determinar dimensiones
            n_pixels = len(depth)
            
            # LiDAR: 256x192 = 49,152 pixels
            if n_pixels == 256 * 192:
                return depth.reshape(192, 256)
            
            # FaceID: 640x480 = 307,200 pixels
            if n_pixels == 640 * 480:
                return depth.reshape(480, 640)
            
            # Intentar diferentes resoluciones comunes
            for h, w in [(144, 192), (180, 240), (270, 360), (360, 480), (540, 720)]:
                if w * h == n_pixels:
                    return depth.reshape(h, w)
            
            # Si no coincide, intentar con aspecto 4:3
            aspect = 4/3
            h_est = int(np.sqrt(n_pixels / aspect))
            w_est = int(h_est * aspect)
            
            if abs(w_est * h_est - n_pixels) < 100:
                return depth.reshape(h_est, w_est)[:,:w_est]
            
            print(f"  [Warning] Dimensiones desconocidas para {depth_path}: {n_pixels} pixels")
            return None
            
        except Exception as e:
            print(f"  [Error] Leyendo {depth_path}: {e}")
            return None
    
    def _read_conf_file(self, z: zipfile.ZipFile, conf_path: str) -> Optional[np.ndarray]:
        """Lee un archivo .conf y lo convierte a numpy array.
        
        Record3D guarda confidence como uint8 comprimido con LZFSE.
        Valores: 0=baja, 1=media, 2=alta confianza.
        """
        try:
            with z.open(conf_path) as f:
                data = f.read()
            
            if not HAS_LZFSE:
                return None
            
            # Descomprimir con LZFSE
            decompressed = self._lzfse_decompress(data)
            
            if decompressed is None:
                return None
            
            # Convertir a uint8
            conf = np.frombuffer(decompressed, dtype=np.uint8)
            
            # Mismas dimensiones que depth
            n_pixels = len(conf)
            
            if n_pixels == 256 * 192:
                return conf.reshape(192, 256)
            elif n_pixels == 640 * 480:
                return conf.reshape(480, 640)
            
            # Intentar mismas dimensiones que depth
            for h, w in [(144, 192), (180, 240), (270, 360), (360, 480)]:
                if w * h == n_pixels:
                    return conf.reshape(h, w)
            
            return None
            
        except Exception as e:
            return None
    
    def extract_frame(self, frame_idx: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """Extrae un frame RGB, depth map y confidence map.
        
        Args:
            frame_idx: índice del frame (0-based)
            
        Returns:
            tuple: (rgb_frame_bgr, depth_map, confidence_map) o (None, None, None)
        """
        rgb_files, depth_files, conf_files = self._get_frame_files()
        
        if frame_idx >= len(rgb_files):
            return None, None, None
        
        with zipfile.ZipFile(self.path, 'r') as z:
            # Leer RGB
            rgb_name = rgb_files[frame_idx]
            with z.open(rgb_name) as f:
                data = np.frombuffer(f.read(), np.uint8)
                rgb_frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            
            # Leer depth
            depth_map = None
            if frame_idx < len(depth_files):
                depth_name = depth_files[frame_idx]
                depth_map = self._read_depth_file(z, depth_name)
            
            # Leer confidence
            conf_map = None
            if frame_idx < len(conf_files):
                conf_name = conf_files[frame_idx]
                conf_map = self._read_conf_file(z, conf_name)
            
            return rgb_frame, depth_map, conf_map
    
    def extract_all(self) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray]]:
        """Extrae todos los frames RGB, depth maps y confidence maps.
        
        Returns:
            tuple: (list_of_rgb_frames, list_of_depth_maps, list_of_conf_maps)
        """
        rgb_files, depth_files, conf_files = self._get_frame_files()
        
        frames = []
        depths = []
        confs = []
        
        with zipfile.ZipFile(self.path, 'r') as z:
            for i, rgb_name in enumerate(rgb_files):
                # Frame RGB
                with z.open(rgb_name) as f:
                    data = np.frombuffer(f.read(), np.uint8)
                    rgb = cv2.imdecode(data, cv2.IMREAD_COLOR)
                    frames.append(rgb)
                
                # Depth correspondiente
                if i < len(depth_files):
                    depth_name = depth_files[i]
                    depth = self._read_depth_file(z, depth_name)
                    depths.append(depth)
                else:
                    depths.append(None)
                
                # Confidence correspondiente
                if i < len(conf_files):
                    conf_name = conf_files[i]
                    conf = self._read_conf_file(z, conf_name)
                    confs.append(conf)
                else:
                    confs.append(None)
        
        self._frames = frames
        self._depths = depths
        return frames, depths, confs
    
    def save_frames(self, output_dir: str, max_frames: int = None) -> List[dict]:
        """Guarda frames RGB, depth maps y confidence maps como archivos individuales.
        
        Args:
            output_dir: directorio de salida
            max_frames: número máximo de frames a guardar (None = todos)
            
        Returns:
            lista de dicts con info de cada frame guardado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        frames, depths, confs = self.extract_all()
        
        if max_frames is not None:
            frames = frames[:max_frames]
            depths = depths[:max_frames]
            confs = confs[:max_frames]
        
        saved = []
        
        for i, (rgb, depth, conf) in enumerate(zip(frames, depths, confs)):
            # Guardar RGB
            rgb_path = output_path / f"frame_{i:06d}.png"
            cv2.imwrite(str(rgb_path), rgb)
            
            # Guardar depth como numpy
            depth_path = output_path / f"depth_{i:06d}.npy"
            if depth is not None:
                np.save(str(depth_path), depth)
            
            # Guardar confidence como numpy
            conf_path = output_path / f"conf_{i:06d}.npy"
            if conf is not None:
                np.save(str(conf_path), conf)
            
            saved.append({
                'index': i,
                'rgb_path': str(rgb_path),
                'depth_path': str(depth_path) if depth is not None else None,
                'conf_path': str(conf_path) if conf is not None else None,
                'shape': rgb.shape if rgb is not None else None,
                'depth_shape': depth.shape if depth is not None else None,
                'conf_shape': conf.shape if conf is not None else None,
            })
            
            if (i + 1) % 50 == 0:
                depth_info = f"{depth.shape}" if depth is not None else "N/A"
                print(f"  Frame {i}: RGB={rgb.shape}, Depth={depth_info}")
        
        print(f"\n  Total: {len(saved)} frames guardados en {output_path}")
        return saved


def list_r3d_files(directory: str) -> List[Path]:
    """Lista todos los archivos .r3d en un directorio."""
    return list(Path(directory).glob("**/*.r3d"))


def quick_info(r3d_path: str) -> dict:
    """Obtiene información rápida de un archivo .r3d."""
    parser = R3DParser(r3d_path)
    return parser.get_info()


def extract_r3d(r3d_path: str, output_dir: str, max_frames: int = None) -> List[dict]:
    """Extrae frames y depths de un archivo .r3d."""
    parser = R3DParser(r3d_path)
    return parser.save_frames(output_dir, max_frames)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python r3d_parser.py <archivo.r3d> [directorio_salida]")
        sys.exit(1)
    
    r3d_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/r3d_extracted"
    
    print(f"Extracting: {r3d_path}")
    print(f"Output: {output_dir}\n")
    
    parser = R3DParser(r3d_path)
    info = parser.get_info()
    print("Info del archivo:")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()
    
    saved = extract_r3d(r3d_path, output_dir)
    print(f"\n¡Listo! {len(saved)} frames extraídos.")
