"""
Module for updating MMD (MET Norway Metadata) XML files.

Provides an object-oriented interface for applying multiple updates to MMD files
in a scalable and maintainable way.

Author: Transform Coherence Products
"""

import lxml.etree as ET
from pathlib import Path
from typing import Optional, Callable, Iterable
import hashlib


class MMDUpdater:
    """
    A class for updating MMD XML files with various metadata changes.
    
    Supports a flexible update mechanism through registered update functions
    that can be applied to the XML document.
    """
    
    # MMD namespace
    NAMESPACE = {'mmd': 'http://www.met.no/schema/mmd'}
    SENTINEL_LICENSE_TEXT = (
        "The use of these data are covered by the Legal notice on the use of "
        "Copernicus Sentinel Data and Service Information at "
        "https://sentinels.copernicus.eu/documents/247904/690755/"
        "Sentinel_Data_Legal_Notice"
    )
    S1_PLATFORM_LOOKUP = {
        "S1A": {
            "short_name": "Sentinel-1A",
            "long_name": "Sentinel-1A",
            "resource": "https://www.wmo-sat.info/oscar/satellites/view/sentinel_1a",
        },
        "S1B": {
            "short_name": "Sentinel-1B",
            "long_name": "Sentinel-1B",
            "resource": "https://www.wmo-sat.info/oscar/satellites/view/sentinel_1b",
        },
        "S1C": {
            "short_name": "Sentinel-1C",
            "long_name": "Sentinel-1C",
            "resource": "https://www.wmo-sat.info/oscar/satellites/view/sentinel_1c",
        },
        "S1D": {
            "short_name": "Sentinel-1D",
            "long_name": "Sentinel-1D",
            "resource": "https://www.wmo-sat.info/oscar/satellites/view/sentinel_1d",
        },
    }
    
    def __init__(self, file_path: str):
        """
        Initialize the MMDUpdater with an MMD XML file.
        
        Args:
            file_path (str): Path to the MMD XML file to update
            
        Raises:
            FileNotFoundError: If the file does not exist
            ET.XMLSyntaxError: If the file is not valid XML
        """
        self.file_path = Path(file_path)
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"MMD file not found: {file_path}")
        
        try:
            self.tree = ET.parse(self.file_path)
            self.root = self.tree.getroot()
        except ET.XMLSyntaxError as e:
            raise ET.XMLSyntaxError(f"Invalid XML in {file_path}: {e}")
    
    def _find_element(self, tag_path: str) -> Optional[ET._Element]:
        """
        Find an element by tag path with MMD namespace.
        
        Args:
            tag_path (str): Tag path (e.g., './/mmd:dataset_production_status' or 'mmd:project/mmd:short_name')
            
        Returns:
            ET._Element or None: The found element or None
        """
        # Convert '//' to './' for lxml compatibility
        if tag_path.startswith('//'):
            tag_path = '.' + tag_path
        
        elements = self.root.findall(tag_path, self.NAMESPACE)
        return elements[0] if elements else None
    
    def _find_all_elements(self, tag_path: str) -> list:
        """
        Find all elements matching a tag path.
        
        Args:
            tag_path (str): Tag path
            
        Returns:
            list: List of matching elements
        """
        # Convert '//' to './' for lxml compatibility
        if tag_path.startswith('//'):
            tag_path = '.' + tag_path
        
        return self.root.findall(tag_path, self.NAMESPACE)

    def _ns_tag(self, local_name: str) -> str:
        """Build a namespaced tag for new elements."""
        return f"{{{self.NAMESPACE['mmd']}}}{local_name}"

    def _get_or_create_child(self, parent: ET._Element, child_name: str) -> ET._Element:
        """Get an existing direct child by local name or create it."""
        for child in parent:
            if ET.QName(child).localname == child_name:
                return child
        return ET.SubElement(parent, self._ns_tag(child_name))
    
    def update_element_text(self, tag_path: str, new_value: str) -> 'MMDUpdater':
        """
        Update the text content of an element.
        
        Args:
            tag_path (str): Tag path to the element to update (e.g., './/mmd:dataset_production_status')
            new_value (str): New text value
            
        Returns:
            MMDUpdater: Self for method chaining
            
        Raises:
            ValueError: If element is not found
        """
        element = self._find_element(tag_path)
        if element is None:
            raise ValueError(f"Element not found: {tag_path}")
        
        element.text = new_value
        return self
    
    def update_dataset_production_status(self, status: str) -> 'MMDUpdater':
        """
        Update the dataset production status.
        
        Args:
            status (str): New status value (e.g., 'Complete', 'In Progress', 'Not available')
            
        Returns:
            MMDUpdater: Self for method chaining
        """
        return self.update_element_text('//mmd:dataset_production_status', status)
    
    def update_project_short_name(self, short_name: str) -> 'MMDUpdater':
        """
        Update the project short name.
        
        Args:
            short_name (str): New short name for the project
            
        Returns:
            MMDUpdater: Self for method chaining
        """
        return self.update_element_text('//mmd:project/mmd:short_name', short_name)

    def upsert_use_constraint_license(self, license_text: Optional[str] = None) -> 'MMDUpdater':
        """Create or update use constraint license text."""
        text_value = license_text or self.SENTINEL_LICENSE_TEXT

        use_constraint = self._find_element('//mmd:use_constraint')
        if use_constraint is None:
            use_constraint = ET.SubElement(self.root, self._ns_tag('use_constraint'))

        license_elem = self._get_or_create_child(use_constraint, 'license_text')
        license_elem.text = text_value
        return self

    def upsert_data_center(
        self,
        short_name: str = 'METNO',
        long_name: str = 'Norwegian Meteorological Institute',
        url: str = 'https://met.no',
    ) -> 'MMDUpdater':
        """Create or update data_center with normalized METNO structure."""
        data_center = self._find_element('//mmd:data_center')
        if data_center is None:
            data_center = ET.SubElement(self.root, self._ns_tag('data_center'))

        data_center_name = self._get_or_create_child(data_center, 'data_center_name')
        short_elem = self._get_or_create_child(data_center_name, 'short_name')
        long_elem = self._get_or_create_child(data_center_name, 'long_name')
        url_elem = self._get_or_create_child(data_center, 'data_center_url')

        short_elem.text = short_name
        long_elem.text = long_name
        url_elem.text = url
        return self

    def add_sentinel1_platforms(
        self,
        platforms: Iterable[str],
        product_type: str = 'SAR-ARD-L1-COH',
        instrument_short_name: str = 'SAR-C',
        instrument_long_name: str = 'Synthetic Aperture Radar (C-band)',
        instrument_resource: str = 'https://www.wmo-sat.info/oscar/instruments/view/sar_c_sentinel_1',
    ) -> 'MMDUpdater':
        """Add one or more Sentinel-1 platform blocks, with de-duplication by platform."""
        normalized = []
        for platform in platforms:
            p = platform.strip().upper()
            if p not in self.S1_PLATFORM_LOOKUP:
                raise ValueError(f"Unsupported Sentinel-1 platform '{platform}'. Use one of S1A/S1B/S1C/S1D.")
            if p not in normalized:
                normalized.append(p)

        existing_platforms = self._find_all_elements('//mmd:platform')
        existing_short_names = set()
        for platform_elem in existing_platforms:
            short_elem = platform_elem.find('mmd:short_name', self.NAMESPACE)
            if short_elem is not None and short_elem.text:
                existing_short_names.add(short_elem.text.strip())

        insert_after_idx = -1
        for idx, child in enumerate(list(self.root)):
            if ET.QName(child).localname == 'project':
                insert_after_idx = idx

        for p in normalized:
            meta = self.S1_PLATFORM_LOOKUP[p]
            if meta['short_name'] in existing_short_names:
                continue

            platform_elem = ET.Element(self._ns_tag('platform'))
            ET.SubElement(platform_elem, self._ns_tag('short_name')).text = meta['short_name']
            ET.SubElement(platform_elem, self._ns_tag('long_name')).text = meta['long_name']
            ET.SubElement(platform_elem, self._ns_tag('resource')).text = meta['resource']

            instrument_elem = ET.SubElement(platform_elem, self._ns_tag('instrument'))
            ET.SubElement(instrument_elem, self._ns_tag('short_name')).text = instrument_short_name
            ET.SubElement(instrument_elem, self._ns_tag('long_name')).text = instrument_long_name
            ET.SubElement(instrument_elem, self._ns_tag('resource')).text = instrument_resource
            ET.SubElement(instrument_elem, self._ns_tag('product_type')).text = product_type

            insert_after_idx += 1
            self.root.insert(insert_after_idx, platform_elem)

        return self

    def add_related_datasets(self, dataset_names: Iterable[str], relation_type: str) -> 'MMDUpdater':
        """Add related_dataset elements for a relation type, de-duplicated by relation and text."""
        existing_related = self._find_all_elements('//mmd:related_dataset')
        existing_pairs = set()
        for related_elem in existing_related:
            existing_relation_type = related_elem.get('relation_type', '').strip()
            dataset_name = (related_elem.text or '').strip()
            if existing_relation_type and dataset_name:
                existing_pairs.add((existing_relation_type, dataset_name))

        insert_after_idx = -1
        for idx, child in enumerate(list(self.root)):
            local_name = ET.QName(child).localname
            if local_name in {'platform', 'project'}:
                insert_after_idx = idx

        for dataset_name in dataset_names:
            normalized_name = dataset_name.strip()
            if not normalized_name:
                continue

            pair = (relation_type, normalized_name)
            if pair in existing_pairs:
                continue

            related_elem = ET.Element(self._ns_tag('related_dataset'))
            related_elem.set('relation_type', relation_type)
            related_elem.text = normalized_name

            insert_after_idx += 1
            self.root.insert(insert_after_idx, related_elem)
            existing_pairs.add(pair)

        return self

    def add_related_datasets_is_derived_from(self, dataset_names: Iterable[str]) -> 'MMDUpdater':
        """Add related_dataset elements with relation_type=isDerivedFrom."""
        return self.add_related_datasets(dataset_names, 'isDerivedFrom')

    def add_related_datasets_parent(self, dataset_names: Iterable[str]) -> 'MMDUpdater':
        """Add related_dataset elements with relation_type=parent."""
        return self.add_related_datasets(dataset_names, 'parent')

    def update_storage_information_from_file(self, data_file_path: str, file_format: str = 'NetCDF') -> 'MMDUpdater':
        """Populate storage_information with filename, file format, size (MB), and MD5 checksum."""
        data_path = Path(data_file_path)
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_file_path}")

        storage = self._find_element('//mmd:storage_information')
        if storage is None:
            storage = ET.SubElement(self.root, self._ns_tag('storage_information'))

        file_name_elem = self._get_or_create_child(storage, 'file_name')
        file_name_elem.text = data_path.name

        file_format_elem = self._get_or_create_child(storage, 'file_format')
        file_format_elem.text = file_format

        size_mb = data_path.stat().st_size / (1024 * 1024)
        file_size_elem = self._get_or_create_child(storage, 'file_size')
        file_size_elem.set('unit', 'MB')
        file_size_elem.text = f"{size_mb:.2f}"

        checksum_elem = self._get_or_create_child(storage, 'checksum')
        checksum_elem.set('type', 'md5sum')
        checksum_elem.text = self._compute_md5(data_path)
        return self

    def ensure_sios_collection_if_north_above(self, threshold: float = 70.0) -> 'MMDUpdater':
        """Ensure SIOS collection is present directly after NBS when northern extent exceeds threshold."""
        north_elem = self._find_element('//mmd:geographic_extent/mmd:rectangle/mmd:north')
        if north_elem is None or north_elem.text is None:
            return self

        try:
            north_value = float(north_elem.text.strip())
        except ValueError:
            return self

        if north_value <= threshold:
            return self

        collections = [
            c for c in self.root.findall('mmd:collection', self.NAMESPACE)
            if c.text is not None
        ]
        nbs_elem = next((c for c in collections if c.text.strip() == 'NBS'), None)
        sios_elem = next((c for c in collections if c.text.strip() == 'SIOS'), None)

        if nbs_elem is None:
            return self

        root_children = list(self.root)
        nbs_idx = root_children.index(nbs_elem)

        if sios_elem is None:
            sios_elem = ET.Element(self._ns_tag('collection'))
            sios_elem.text = 'SIOS'
        else:
            self.root.remove(sios_elem)

        self.root.insert(nbs_idx + 1, sios_elem)
        return self

    def _compute_md5(self, file_path: Path) -> str:
        """Compute md5 checksum for a file path."""
        digest = hashlib.md5()
        with file_path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(8192), b''):
                digest.update(chunk)
        return digest.hexdigest()
    
    def save(self, output_path: Optional[str] = None, pretty_print: bool = True) -> Path:
        """
        Save the updated MMD file.
        
        Args:
            output_path (str, optional): Path to save the file. If None, overwrites original.
            pretty_print (bool): Whether to format the output with indentation. Default: True
            
        Returns:
            Path: Path to the saved file
        """
        save_path = Path(output_path) if output_path else self.file_path

        if pretty_print:
            # Normalize indentation so inserted nodes do not end up serialized inline.
            try:
                ET.indent(self.tree, space="  ")
            except AttributeError:
                pass
        
        self.tree.write(
            save_path,
            pretty_print=pretty_print,
            xml_declaration=True,
            encoding='UTF-8'
        )
        
        return save_path
    
    def get_element_value(self, tag_path: str) -> Optional[str]:
        """
        Get the text value of an element.
        
        Args:
            tag_path (str): Tag path to the element
            
        Returns:
            str or None: Element text or None if not found
        """
        element = self._find_element(tag_path)
        return element.text if element is not None else None


class MMDUpdatePipeline:
    """
    A pipeline for applying multiple updates to an MMD file in sequence.
    
    Useful for organizing complex update workflows.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the pipeline with an MMD file.
        
        Args:
            file_path (str): Path to the MMD XML file
        """
        self.updater = MMDUpdater(file_path)
        self.updates = []
    
    def add_update(self, update_func: Callable[[MMDUpdater], MMDUpdater]) -> 'MMDUpdatePipeline':
        """
        Add an update function to the pipeline.
        
        Args:
            update_func (Callable): Function that takes MMDUpdater and returns MMDUpdater
            
        Returns:
            MMDUpdatePipeline: Self for method chaining
        """
        self.updates.append(update_func)
        return self
    
    def execute(self) -> MMDUpdater:
        """
        Execute all updates in the pipeline in sequence.
        
        Returns:
            MMDUpdater: The updated MMDUpdater instance
        """
        for update_func in self.updates:
            self.updater = update_func(self.updater)
        
        return self.updater
